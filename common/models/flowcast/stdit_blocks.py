import functools
import math
from typing import Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


approx_gelu = lambda: nn.GELU(approximate="tanh")


class LlamaRMSNorm(nn.Module):
    def __init__(self, hidden_size, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.variance_epsilon = eps

    def forward(self, hidden_states):
        input_dtype = hidden_states.dtype
        hidden_states = hidden_states.to(torch.float32)
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        hidden_states = hidden_states * torch.rsqrt(variance + self.variance_epsilon)
        return self.weight * hidden_states.to(input_dtype)


def get_layernorm(hidden_size: torch.Tensor, eps: float, affine: bool):
    return nn.LayerNorm(hidden_size, eps, elementwise_affine=affine)


def modulate(x, shift, scale):
    return x * (1 + scale) + shift


class PatchEmbed3D(nn.Module):
    def __init__(
        self,
        patch_size=(2, 4, 4),
        in_chans=3,
        embed_dim=96,
        norm_layer=None,
        flatten=True,
    ):
        super().__init__()
        self.patch_size = patch_size
        self.flatten = flatten
        self.in_chans = in_chans
        self.embed_dim = embed_dim
        self.proj = nn.Conv3d(
            in_chans,
            embed_dim,
            kernel_size=patch_size,
            stride=patch_size,
        )
        self.norm = norm_layer(embed_dim) if norm_layer is not None else None

    def forward(self, x):
        _, _, depth, height, width = x.size()
        if width % self.patch_size[2] != 0:
            x = F.pad(x, (0, self.patch_size[2] - width % self.patch_size[2]))
        if height % self.patch_size[1] != 0:
            x = F.pad(x, (0, 0, 0, self.patch_size[1] - height % self.patch_size[1]))
        if depth % self.patch_size[0] != 0:
            x = F.pad(x, (0, 0, 0, 0, 0, self.patch_size[0] - depth % self.patch_size[0]))
        x = self.proj(x)
        if self.norm is not None:
            depth, width_h, width_w = x.size(2), x.size(3), x.size(4)
            x = x.flatten(2).transpose(1, 2)
            x = self.norm(x)
            x = x.transpose(1, 2).view(-1, self.embed_dim, depth, width_h, width_w)
        if self.flatten:
            x = x.flatten(2).transpose(1, 2)
        return x


class Attention(nn.Module):
    def __init__(
        self,
        dim: int,
        num_heads: int = 8,
        qkv_bias: bool = False,
        qk_norm: bool = False,
        attn_drop: float = 0.0,
        proj_drop: float = 0.0,
        norm_layer: nn.Module = LlamaRMSNorm,
        enable_flash_attn: bool = False,
        rope=None,
    ) -> None:
        super().__init__()
        assert dim % num_heads == 0, "dim should be divisible by num_heads"
        self.dim = dim
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim**-0.5
        self.enable_flash_attn = enable_flash_attn
        self.qkv = nn.Linear(dim, dim * 3, bias=qkv_bias)
        self.q_norm = norm_layer(self.head_dim) if qk_norm else nn.Identity()
        self.k_norm = norm_layer(self.head_dim) if qk_norm else nn.Identity()
        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(dim, dim)
        self.proj_drop = nn.Dropout(proj_drop)

        self.rope = False
        if rope is not None:
            self.rope = True
            self.rotary_emb = rope

        self.is_causal = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, num_tokens, channels = x.shape
        enable_flash_attn = self.enable_flash_attn and (num_tokens > batch_size)
        qkv = self.qkv(x)
        qkv_shape = (batch_size, num_tokens, 3, self.num_heads, self.head_dim)
        qkv = qkv.view(qkv_shape).permute(2, 0, 3, 1, 4)
        q, k, v = qkv.unbind(0)
        q, k = self.q_norm(q), self.k_norm(k)
        if self.rope:
            q = self.rotary_emb(q)
            k = self.rotary_emb(k)
        dtype = q.dtype
        q = q * self.scale
        attn = q @ k.transpose(-2, -1)
        attn = attn.to(torch.float32)
        if self.is_causal:
            causal_mask = torch.tril(torch.ones_like(attn), diagonal=0)
            causal_mask = torch.where(causal_mask.bool(), 0, float("-inf"))
            attn += causal_mask
        attn = attn.softmax(dim=-1)
        attn = attn.to(dtype)
        attn = self.attn_drop(attn)
        x = attn @ v

        if not enable_flash_attn:
            x = x.transpose(1, 2)
        x = x.reshape(batch_size, num_tokens, channels)
        x = self.proj(x)
        x = self.proj_drop(x)
        return x


class FinalLayer(nn.Module):
    def __init__(self, hidden_size, num_patch, out_channels):
        super().__init__()
        self.norm_final = nn.LayerNorm(hidden_size, elementwise_affine=False, eps=1e-6)
        self.linear = nn.Linear(hidden_size, num_patch * out_channels, bias=True)
        self.scale_shift_table = nn.Parameter(torch.randn(2, hidden_size) / hidden_size**0.5)

    def forward(self, x):
        shift, scale = self.scale_shift_table[None].chunk(2, dim=1)
        x = modulate(self.norm_final(x), shift, scale)
        x = self.linear(x)
        return x


class TimestepEmbedder(nn.Module):
    def __init__(self, hidden_size, frequency_embedding_size=256):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(frequency_embedding_size, hidden_size, bias=True),
            nn.SiLU(),
            nn.Linear(hidden_size, hidden_size, bias=True),
        )
        self.frequency_embedding_size = frequency_embedding_size

    @staticmethod
    def timestep_embedding(t, dim, max_period=10000):
        half = dim // 2
        freqs = torch.exp(
            -math.log(max_period)
            * torch.arange(start=0, end=half, dtype=torch.float32)
            / half
        )
        freqs = freqs.to(device=t.device)
        args = t[:, None].float() * freqs[None]
        embedding = torch.cat([torch.cos(args), torch.sin(args)], dim=-1)
        if dim % 2:
            embedding = torch.cat([embedding, torch.zeros_like(embedding[:, :1])], dim=-1)
        return embedding

    def forward(self, t, dtype):
        t_freq = self.timestep_embedding(t, self.frequency_embedding_size)
        if t_freq.dtype != dtype:
            t_freq = t_freq.to(dtype)
        return self.mlp(t_freq)


class PositionEmbedding3D(nn.Module):
    def __init__(
        self,
        embed_dim: int = 1024,
        H: int = 8,
        W: int = 8,
        T: int = 5,
        spatial_interpolation_scale: float = 1.0,
        temporal_interpolation_scale: float = 1.0,
    ) -> None:
        super().__init__()
        self.embed_dim = embed_dim
        self.H = H
        self.W = W
        self.T = T
        self.spatial_interpolation_scale = spatial_interpolation_scale
        self.temporal_interpolation_scale = temporal_interpolation_scale
        pos_embedding = get_3d_sincos_pos_embed(
            self.embed_dim,
            (H, W),
            T,
            self.spatial_interpolation_scale,
            self.temporal_interpolation_scale,
        )
        self.register_buffer("pos_embedding", torch.from_numpy(pos_embedding), persistent=True)

    def forward(self, H, W, T, device, xdtype):
        if self.H != H or self.W != W or self.T != T:
            pos_embedding = get_3d_sincos_pos_embed(
                self.embed_dim,
                (H, W),
                T,
                self.spatial_interpolation_scale,
                self.temporal_interpolation_scale,
            )
            pos_embedding = torch.from_numpy(pos_embedding)
        else:
            pos_embedding = self.pos_embedding
        return pos_embedding.to(device, dtype=xdtype)


def get_3d_sincos_pos_embed(
    embed_dim: int,
    spatial_size: Union[int, Tuple[int, int]],
    temporal_size: int,
    spatial_interpolation_scale: float = 1.0,
    temporal_interpolation_scale: float = 1.0,
) -> np.ndarray:
    if embed_dim % 4 != 0:
        raise ValueError("`embed_dim` must be divisible by 4")
    if isinstance(spatial_size, int):
        spatial_size = (spatial_size, spatial_size)

    embed_dim_spatial = 3 * embed_dim // 4
    embed_dim_temporal = embed_dim // 4

    grid_h = np.arange(spatial_size[1], dtype=np.float32) / spatial_interpolation_scale
    grid_w = np.arange(spatial_size[0], dtype=np.float32) / spatial_interpolation_scale
    grid = np.meshgrid(grid_w, grid_h)
    grid = np.stack(grid, axis=0)
    grid = grid.reshape([2, 1, spatial_size[1], spatial_size[0]])
    pos_embed_spatial = get_2d_sincos_pos_embed_from_grid(embed_dim_spatial, grid)

    grid_t = np.arange(temporal_size, dtype=np.float32) / temporal_interpolation_scale
    pos_embed_temporal = get_1d_sincos_pos_embed_from_grid(embed_dim_temporal, grid_t)

    pos_embed_spatial = pos_embed_spatial[np.newaxis, :, :]
    pos_embed_spatial = np.repeat(pos_embed_spatial, temporal_size, axis=0)

    pos_embed_temporal = pos_embed_temporal[:, np.newaxis, :]
    pos_embed_temporal = np.repeat(
        pos_embed_temporal,
        spatial_size[0] * spatial_size[1],
        axis=1,
    )

    return np.concatenate([pos_embed_temporal, pos_embed_spatial], axis=-1)


def get_2d_sincos_pos_embed_from_grid(embed_dim, grid):
    if embed_dim % 2 != 0:
        raise ValueError("embed_dim must be divisible by 2")
    emb_h = get_1d_sincos_pos_embed_from_grid(embed_dim // 2, grid[0])
    emb_w = get_1d_sincos_pos_embed_from_grid(embed_dim // 2, grid[1])
    return np.concatenate([emb_h, emb_w], axis=1)


def get_1d_sincos_pos_embed_from_grid(embed_dim, pos):
    if embed_dim % 2 != 0:
        raise ValueError("embed_dim must be divisible by 2")
    omega = np.arange(embed_dim // 2, dtype=np.float64)
    omega /= embed_dim / 2.0
    omega = 1.0 / 10000**omega

    pos = pos.reshape(-1)
    out = np.einsum("m,d->md", pos, omega)
    emb_sin = np.sin(out)
    emb_cos = np.cos(out)
    return np.concatenate([emb_sin, emb_cos], axis=1)
