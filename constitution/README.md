# 已迁移

认知宪法与 Runtime Policy 已迁移至：

```text
runtime/
  constitution/
  policy/
```

Constitution **不再写入 Memory Store**，而是在 Gateway BOOT 时编译为 `data/runtime/constitution.bin`。

请编辑 `runtime/` 下的源文件，而非通过文档导入上传 Constitution。
