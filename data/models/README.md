# data/models/ — 可选的 canonical model index（Phase 1 预留，当前为空）。
#
# Provider 实际暴露的模型能力保存在：
#     data/providers/<provider>/models.yaml
# 那里是能力的唯一事实源（Provider-specific override）。
#
# 如果未来需要建立跨 Provider 的规范化模型身份（canonical model identity），
# 在本目录额外维护索引文件。但该索引**不能覆盖** Provider 实际暴露的能力、
# 上下文、倍率、可用性或限流。
