from collections.abc import Iterable

import numpy as np
import torch
import torch.nn as nn
from einops import rearrange
from rotary_embedding_torch import RotaryEmbedding
from timm.models.layers import DropPath
from timm.models.vision_transformer import Mlp
from torch.utils.checkpoint import checkpoint, checkpoint_sequential
from transformers import PreTrainedModel, PretrainedConfig

from .stdit_blocks import (
    Attention,
    FinalLayer,
    PatchEmbed3D,
    PositionEmbedding3D,
    TimestepEmbedder,
    approx_gelu,
    get_layernorm,
    modulate,
)


def auto_grad_checkpoint(module, *args, **kwargs):
    if getattr(module, "grad_checkpointing", False):
        if not isinstance(module, Iterable):
            return checkpoint(module, *args, use_reentrant=False, **kwargs)
        gc_step = module[0].grad_checkpointing_step
        return checkpoint_sequential(module, gc_step, *args, use_reentrant=False, **kwargs)
    return module(*args, **kwargs)


class STDiTBlock(nn.Module):
    def __init__(
        self,
        hidden_size,
        num_heads,
        mlp_ratio=4.0,
        drop_path=0.0,
        rope=None,
        qk_norm=False,
        attn_type="spatial",
    ):
        super().__init__()
        self.attn_type = attn_type
        self.hidden_size = hidden_size
        self.norm1 = get_layernorm(hidden_size, eps=1e-6, affine=False)
        self.attn = Attention(
            hidden_size,
            num_heads=num_heads,
            qkv_bias=True,
            qk_norm=qk_norm,
            rope=rope,
        )
        self.norm2 = get_layernorm(hidden_size, eps=1e-6, affine=False)
        self.mlp = Mlp(
            in_features=hidden_size,
            hidden_features=int(hidden_size * mlp_ratio),
            act_layer=approx_gelu,
            drop=0,
        )
        self.drop_path = DropPath(drop_path) if drop_path > 0.0 else nn.Identity()
        self.scale_shift_table = nn.Parameter(torch.randn(6, hidden_size) / hidden_size**0.5)

    def forward(self, x, t, T=None, S=None):
        batch_size, _, _ = x.shape
        shift_msa, scale_msa, gate_msa, shift_mlp, scale_mlp, gate_mlp = (
            self.scale_shift_table[None] + t.reshape(batch_size, 6, -1)
        ).chunk(6, dim=1)
        x_m = modulate(self.norm1(x), shift_msa, scale_msa)
        if self.attn_type == "temporal":
            x_m = rearrange(x_m, "B (T S) C -> (B S) T C", T=T, S=S)
            x_m = self.attn(x_m)
            x_m = rearrange(x_m, "(B S) T C -> B (T S) C", T=T, S=S)
        elif self.attn_type == "spatial":
            x_m = rearrange(x_m, "B (T S) C -> (B T) S C", T=T, S=S)
            x_m = self.attn(x_m)
            x_m = rearrange(x_m, "(B T) S C -> B (T S) C", T=T, S=S)
        else:
            x_m = self.attn(x_m)
        x = x + self.drop_path(gate_msa * x_m)
        x_m = modulate(self.norm2(x), shift_mlp, scale_mlp)
        x_m = self.mlp(x_m)
        x = x + self.drop_path(gate_mlp * x_m)
        return x


class STDiTConfig(PretrainedConfig):
    def __init__(
        self,
        input_size=(None, None, None),
        in_channels=8,
        patch_size=(1, 2, 2),
        hidden_size=1152,
        depth=28,
        num_heads=16,
        mlp_ratio=4.0,
        drop_path=0.0,
        qk_norm=True,
        only_train_temporal=False,
        **kwargs,
    ):
        self.input_size = input_size
        self.in_channels = in_channels
        self.patch_size = patch_size
        self.hidden_size = hidden_size
        self.depth = depth
        self.num_heads = num_heads
        self.mlp_ratio = mlp_ratio
        self.drop_path = drop_path
        self.qk_norm = qk_norm
        self.only_train_temporal = only_train_temporal
        super().__init__(**kwargs)


class STDiT(PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.in_channels = config.in_channels
        self.out_channels = config.in_channels
        self.depth = config.depth
        self.mlp_ratio = config.mlp_ratio
        self.hidden_size = config.hidden_size
        self.num_heads = config.num_heads
        self.drop_path = config.drop_path
        self.patch_size = config.patch_size
        self.pos_embed = PositionEmbedding3D(config.hidden_size)
        self.rope = RotaryEmbedding(dim=self.hidden_size // self.num_heads)
        self.x_embedder = PatchEmbed3D(
            config.patch_size,
            config.in_channels * 2,
            config.hidden_size,
        )
        self.t_embedder = TimestepEmbedder(config.hidden_size)
        self.idx_embedder = TimestepEmbedder(config.hidden_size)
        self.t_block = nn.Sequential(
            nn.SiLU(),
            nn.Linear(config.hidden_size * 2, 6 * config.hidden_size, bias=True),
        )
        drop_path = [x.item() for x in torch.linspace(0, self.drop_path, config.depth)]
        self.spatial_blocks = nn.ModuleList(
            [
                STDiTBlock(
                    hidden_size=config.hidden_size,
                    num_heads=config.num_heads,
                    mlp_ratio=config.mlp_ratio,
                    drop_path=drop_path[i],
                    qk_norm=config.qk_norm,
                    attn_type="spatial",
                )
                for i in range(config.depth)
            ]
        )
        self.temporal_blocks = nn.ModuleList(
            [
                STDiTBlock(
                    hidden_size=config.hidden_size,
                    num_heads=config.num_heads,
                    mlp_ratio=config.mlp_ratio,
                    drop_path=drop_path[i],
                    qk_norm=config.qk_norm,
                    attn_type="temporal",
                    rope=self.rope.rotate_queries_or_keys,
                )
                for i in range(config.depth)
            ]
        )
        self.spatiotemporal_blocks = nn.ModuleList(
            [
                STDiTBlock(
                    hidden_size=config.hidden_size,
                    num_heads=config.num_heads,
                    mlp_ratio=config.mlp_ratio,
                    drop_path=drop_path[i],
                    qk_norm=config.qk_norm,
                    attn_type="spatiotemporal",
                )
                for i in range(config.depth // 2)
            ]
        )
        self.final_layer = FinalLayer(config.hidden_size, np.prod(self.patch_size), self.out_channels)

    def get_dynamic_size(self, x):
        _, _, T, H, W = x.size()
        if T % self.patch_size[0] != 0:
            T += self.patch_size[0] - T % self.patch_size[0]
        if H % self.patch_size[1] != 0:
            H += self.patch_size[1] - H % self.patch_size[1]
        if W % self.patch_size[2] != 0:
            W += self.patch_size[2] - W % self.patch_size[2]
        return (T // self.patch_size[0], H // self.patch_size[1], W // self.patch_size[2])

    def forward(self, x, time, cond, idx=None):
        x = torch.cat((cond, x), dim=1)
        _, _, Tx, Hx, Wx = x.size()
        T, H, W = self.get_dynamic_size(x)
        S = H * W
        pos_emb = self.pos_embed(H, W, T, x.device, x.dtype)
        timestep = self.t_embedder(time, dtype=x.dtype)
        idx = self.idx_embedder(idx, dtype=x.dtype)
        t_mlp = self.t_block(torch.cat([timestep, idx], dim=1))
        x = self.x_embedder(x)
        x = rearrange(x, "B (T S) C -> B T S C", T=T, S=S)
        x += pos_emb
        x = rearrange(x, "B T S C -> B (T S) C", T=T, S=S)
        itr = 0
        for spatial_block, temporal_block in zip(self.spatial_blocks, self.temporal_blocks):
            x = auto_grad_checkpoint(spatial_block, x, t_mlp, T, S)
            x = auto_grad_checkpoint(temporal_block, x, t_mlp, T, S)
            if itr % 2 == 0:
                x = auto_grad_checkpoint(self.spatiotemporal_blocks[itr // 2], x, t_mlp, T, S)
            itr += 1
        x = self.final_layer(x)
        x = self.unpatchify(x, T, H, W, Tx, Hx, Wx)
        return x.to(torch.float32)

    def unpatchify(self, x, N_t, N_h, N_w, R_t, R_h, R_w):
        T_p, H_p, W_p = self.patch_size
        x = rearrange(
            x,
            "B (N_t N_h N_w) (T_p H_p W_p C_out) -> B C_out (N_t T_p) (N_h H_p) (N_w W_p)",
            N_t=N_t,
            N_h=N_h,
            N_w=N_w,
            T_p=T_p,
            H_p=H_p,
            W_p=W_p,
            C_out=self.out_channels,
        )
        return x[:, :, :R_t, :R_h, :R_w]
