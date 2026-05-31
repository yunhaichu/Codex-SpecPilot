# INJECTION

## Start Work Rule
当用户输入"开始工作"时，Codex 必须：
1. 读取 PROJECT_SPEC.md。
2. 按 Development Plan 找到第一个未完成任务。
3. 只执行当前任务。
4. 每轮结束时说明：
     - 本轮处理了哪个 TASK
     - 修改了哪些文件
     - 做了什么验证
     - 下一步是什么
5. 不允许修改 Protected Scope。

## End Work Rule
当所有任务完成且 Acceptance Criteria 满足时，Codex 必须：
1. 停止继续开发。
2. 更新 COMPLETION_REPORT.md。
3. 输出最终完成摘要。
