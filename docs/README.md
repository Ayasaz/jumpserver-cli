# docs assets

放置 README 用到的演示素材。

- `repl-demo.gif` — REPL 交互模式演示(README 顶部引用)。尚未录制,先用占位。

## 录制建议

```bash
# 方式一:vhs(https://github.com/charmbracelet/vhs)
vhs repl-demo.tape   # 输出 repl-demo.gif

# 方式二:asciinema + agg
asciinema rec repl-demo.cast
agg repl-demo.cast repl-demo.gif
```

录制内容建议:`auth login` → `asset list --type host` → `--interactive` 下用 Tab 补全跑两条命令。
