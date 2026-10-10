# 虚构便签：完整的源码审查示例

这是脱敏教学夹具，不是真实业务项目，也不是已通过验收的产品。

输入：project/index.html。范围内只有一个页面、三个逻辑实例（表单、输入、清空按钮）。输出：audit.json、coverage.md、review.md。所有实例都有蓝图、处置和回归设计；运行检查保留 blocked。

从技能根目录执行：

```sh
python3 -B examples/source-only/verify_fixture.py
python3 -B scripts/audit_ledger.py check examples/source-only/audit.json --require-plan
python3 -B scripts/audit_ledger.py check examples/source-only/audit.json --require-complete
```

退出码依次为 0、0、2。静态脚本只验证标签关联、按钮类型与名称；不能证明点击、键盘、布局或安全已经通过。evidence.txt 记录打包时实际运行结果。修复建议尚未实施，示例故意保留缺失行为，以展示如何记录确认的源码问题和未验证的运行影响。
