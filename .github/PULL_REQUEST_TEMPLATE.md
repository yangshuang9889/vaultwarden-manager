## 这个 PR 做了什么

<!-- 一句话说明目的，例如：修复备份恢复在含中文路径下解压失败 -->

关联 Issue：<!-- #123，没有就写「无」 -->

## 改动类型

- [ ] 缺陷修复（不改变既有行为）
- [ ] 新功能
- [ ] 重构 / 代码整理（无功能变化）
- [ ] 文档 / 构建 / CI
- [ ] 其他：

## 改动清单

<!-- 列出主要文件与要点，便于快速 review -->
- 

## 自测情况

- 测试环境：Windows <!-- 版本号 --> / Python <!-- 3.11.x -->
- 测试方式：<!-- 真实点击验证 / tests 目录脚本 / 仅静态检查 -->
- 结果：

```
粘贴关键输出或截图说明（请脱敏：不要含 ADMIN_TOKEN、私钥、个人路径、真实内网 IP）
```

## 提交前检查清单

- [ ] 已阅读 [DEV.md](../blob/main/DEV.md) 的模块结构与开发约定
- [ ] 已同步更新 [CHANGELOG.md](../blob/main/CHANGELOG.md) 的 `Unreleased` 或对应版本段
- [ ] 版本号保持一致：`vwm/ui.py` 的 `VERSION`、`vwm/__init__.py` 的 `__version__`、README、CHANGELOG
- [ ] 未提交任何敏感内容：`.env`、`config.json`、`ADMIN_TOKEN`、`ssl\*.pem`、私钥、个人绝对路径、真实内网 IP
- [ ] 未提交构建产物：`dist\`、`build\`、`*.spec`、`__pycache__\`
- [ ] 本地已执行 `python .github/scripts/check_repo.py` 且全部通过
- [ ] 改动不破坏模块依赖方向（config → service/deploy/cert/backup/logs/network → ui → app）
