"""Vendored WASB ball-detection network (HRNet-W16, narrow).

Source: https://github.com/nttcom/WASB-SBDT (BMVC2023, "Widely Applicable Strong
Baseline for Sports Ball Detection and Tracking"). Architecture kept byte-for-byte
compatible with the published tennis checkpoint (wasb_tennis_best.pth.tar) so its
model_state_dict loads cleanly.

Config (src/configs/model/wasb.yaml): 3 input frames (9 channels) at 512x288, stem
strides [1,1] (full-resolution output), HRNet stages with branch widths
[32] / [16,32] / [16,32,64] / [16,32,64,128]; a single 1x1 final layer maps the
highest-resolution branch (16ch) to 3 heatmaps (one per input frame).
"""

import torch
import torch.nn as nn

BN_MOMENTUM = 0.1


def conv3x3(in_planes, out_planes, stride=1):
    return nn.Conv2d(in_planes, out_planes, 3, stride=stride, padding=1, bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super().__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes, momentum=BN_MOMENTUM)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes, momentum=BN_MOMENTUM)
        self.downsample = downsample

    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        if self.downsample is not None:
            residual = self.downsample(x)
        return self.relu(out + residual)


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super().__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes, momentum=BN_MOMENTUM)
        self.conv2 = nn.Conv2d(planes, planes, 3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes, momentum=BN_MOMENTUM)
        self.conv3 = nn.Conv2d(planes, planes * self.expansion, 1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * self.expansion, momentum=BN_MOMENTUM)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample

    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        if self.downsample is not None:
            residual = self.downsample(x)
        return self.relu(out + residual)


blocks_dict = {"BASIC": BasicBlock, "BOTTLENECK": Bottleneck}


class HighResolutionModule(nn.Module):
    def __init__(self, num_branches, block, num_blocks, num_inchannels, num_channels,
                 multi_scale_output=True):
        super().__init__()
        self.num_branches = num_branches
        self.num_inchannels = num_inchannels
        self.multi_scale_output = multi_scale_output
        self.branches = self._make_branches(num_branches, block, num_blocks, num_channels)
        self.fuse_layers = self._make_fuse_layers()
        self.relu = nn.ReLU(inplace=True)

    def _make_one_branch(self, i, block, num_blocks, num_channels, stride=1):
        downsample = None
        if stride != 1 or self.num_inchannels[i] != num_channels[i] * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.num_inchannels[i], num_channels[i] * block.expansion, 1, stride, bias=False),
                nn.BatchNorm2d(num_channels[i] * block.expansion, momentum=BN_MOMENTUM),
            )
        layers = [block(self.num_inchannels[i], num_channels[i], stride, downsample)]
        self.num_inchannels[i] = num_channels[i] * block.expansion
        for _ in range(1, num_blocks[i]):
            layers.append(block(self.num_inchannels[i], num_channels[i]))
        return nn.Sequential(*layers)

    def _make_branches(self, num_branches, block, num_blocks, num_channels):
        return nn.ModuleList(
            [self._make_one_branch(i, block, num_blocks, num_channels) for i in range(num_branches)]
        )

    def _make_fuse_layers(self):
        if self.num_branches == 1:
            return None
        nb, nic = self.num_branches, self.num_inchannels
        fuse_layers = []
        for i in range(nb if self.multi_scale_output else 1):
            fuse_layer = []
            for j in range(nb):
                if j > i:
                    fuse_layer.append(nn.Sequential(
                        nn.Conv2d(nic[j], nic[i], 1, 1, 0, bias=False),
                        nn.BatchNorm2d(nic[i], momentum=BN_MOMENTUM),
                        nn.Upsample(scale_factor=2 ** (j - i), mode="nearest"),
                    ))
                elif j == i:
                    fuse_layer.append(None)
                else:
                    convs = []
                    for k in range(i - j):
                        if k == i - j - 1:
                            convs.append(nn.Sequential(
                                nn.Conv2d(nic[j], nic[i], 3, 2, 1, bias=False),
                                nn.BatchNorm2d(nic[i], momentum=BN_MOMENTUM),
                            ))
                        else:
                            convs.append(nn.Sequential(
                                nn.Conv2d(nic[j], nic[j], 3, 2, 1, bias=False),
                                nn.BatchNorm2d(nic[j], momentum=BN_MOMENTUM),
                                nn.ReLU(inplace=True),
                            ))
                    fuse_layer.append(nn.Sequential(*convs))
            fuse_layers.append(nn.ModuleList(fuse_layer))
        return nn.ModuleList(fuse_layers)

    def get_num_inchannels(self):
        return self.num_inchannels

    def forward(self, x):
        if self.num_branches == 1:
            return [self.branches[0](x[0])]
        for i in range(self.num_branches):
            x[i] = self.branches[i](x[i])
        x_fuse = []
        for i in range(len(self.fuse_layers)):
            y = x[0] if i == 0 else self.fuse_layers[i][0](x[0])
            for j in range(1, self.num_branches):
                if i == j:
                    y = y + x[j]
                else:
                    y = y + self.fuse_layers[i][j](x[j])
            x_fuse.append(self.relu(y))
        return x_fuse


class HRNet(nn.Module):
    """WASB HRNet for ball heatmaps. in_channels=9 (3 RGB frames), out=3 heatmaps."""

    def __init__(self, in_channels=9, out_channels=3, stem_strides=(1, 1)):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, 64, 3, stem_strides[0], 1, bias=False)
        self.bn1 = nn.BatchNorm2d(64, momentum=BN_MOMENTUM)
        self.conv2 = nn.Conv2d(64, 64, 3, stem_strides[1], 1, bias=False)
        self.bn2 = nn.BatchNorm2d(64, momentum=BN_MOMENTUM)
        self.relu = nn.ReLU(inplace=True)

        # Stage 1: one bottleneck branch, 64 -> 128.
        self.layer1 = self._make_layer(Bottleneck, 64, 32, 1)
        stage1_out = Bottleneck.expansion * 32  # 128

        self.transition1 = self._make_transition_layer([stage1_out], [16, 32])
        self.stage2, pre2 = self._make_stage(1, 2, [2, 2], [16, 32], BasicBlock, [16, 32])

        self.transition2 = self._make_transition_layer(pre2, [16, 32, 64])
        self.stage3, pre3 = self._make_stage(1, 3, [2, 2, 2], [16, 32, 64], BasicBlock, [16, 32, 64])

        self.transition3 = self._make_transition_layer(pre3, [16, 32, 64, 128])
        self.stage4, pre4 = self._make_stage(1, 4, [2, 2, 2, 2], [16, 32, 64, 128], BasicBlock,
                                             [16, 32, 64, 128], multi_scale_output=True)

        self.final_layers = nn.ModuleList([nn.Conv2d(pre4[0], out_channels, 1, 1, 0)])

    def _make_layer(self, block, inplanes, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(inplanes, planes * block.expansion, 1, stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion, momentum=BN_MOMENTUM),
            )
        layers = [block(inplanes, planes, stride, downsample)]
        inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(inplanes, planes))
        return nn.Sequential(*layers)

    def _make_transition_layer(self, num_channels_pre, num_channels_cur):
        num_pre, num_cur = len(num_channels_pre), len(num_channels_cur)
        transitions = []
        for i in range(num_cur):
            if i < num_pre:
                if num_channels_cur[i] != num_channels_pre[i]:
                    transitions.append(nn.Sequential(
                        nn.Conv2d(num_channels_pre[i], num_channels_cur[i], 3, 1, 1, bias=False),
                        nn.BatchNorm2d(num_channels_cur[i], momentum=BN_MOMENTUM),
                        nn.ReLU(inplace=True),
                    ))
                else:
                    transitions.append(None)
            else:
                convs = []
                for j in range(i + 1 - num_pre):
                    inch = num_channels_pre[-1]
                    outch = num_channels_cur[i] if j == i - num_pre else inch
                    convs.append(nn.Sequential(
                        nn.Conv2d(inch, outch, 3, 2, 1, bias=False),
                        nn.BatchNorm2d(outch, momentum=BN_MOMENTUM),
                        nn.ReLU(inplace=True),
                    ))
                transitions.append(nn.Sequential(*convs))
        return nn.ModuleList(transitions)

    def _make_stage(self, num_modules, num_branches, num_blocks, num_channels, block,
                    num_inchannels, multi_scale_output=True):
        modules = []
        for i in range(num_modules):
            reset = not (not multi_scale_output and i == num_modules - 1)
            modules.append(HighResolutionModule(num_branches, block, num_blocks,
                                                num_inchannels, num_channels, reset))
            num_inchannels = modules[-1].get_num_inchannels()
        return nn.Sequential(*modules), num_inchannels

    def forward(self, x):
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        x = self.layer1(x)

        x_list = []
        for i in range(2):
            x_list.append(self.transition1[i](x) if self.transition1[i] is not None else x)
        y_list = self.stage2(x_list)

        x_list = []
        for i in range(3):
            if self.transition2[i] is not None:
                x_list.append(self.transition2[i](y_list[-1] if i == 2 else y_list[i]))
            else:
                x_list.append(y_list[i])
        y_list = self.stage3(x_list)

        x_list = []
        for i in range(4):
            if self.transition3[i] is not None:
                x_list.append(self.transition3[i](y_list[-1] if i == 3 else y_list[i]))
            else:
                x_list.append(y_list[i])
        y_list = self.stage4(x_list)

        return self.final_layers[0](y_list[0])  # (B, out_channels, H, W)
