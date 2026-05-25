VidGuard Demo 素材替换说明

当前 demo 采用方案 A：预生成结果演示版。
你只需要把真实素材放到本目录，并在 src/data/demoCases.js 中替换路径和文案即可。

建议目录：

public/demo-data/
  videos/
    safe-video.mp4
    single-frame-risk.mp4
    continuous-risk.mp4
    non-continuous-risk.mp4
    aigc-risk.mp4
    aigc-safe.mp4

  keyframes/
    safe-video-1.jpg
    safe-video-2.jpg
    single-frame-risk-1.jpg
    continuous-risk-1.jpg
    continuous-risk-2.jpg
    non-continuous-risk-1.jpg
    non-continuous-risk-2.jpg
    aigc-risk-1.jpg
    aigc-safe-1.jpg

  masks/
    可选：实体分割图、带框图、风险标注图

  reports/
    可选：每个样例的完整检测报告 JSON

推荐至少提供 4 个视频检测样例：
1. 合规视频
2. 单帧显性违规
3. 多帧连续违规
4. 多帧非连续隐性违规

推荐至少提供 2 个 AIGC 合规生成样例：
1. 高风险 prompt 对应的拦截样例
2. 合规 prompt 对应的通过样例

每个视频最好提供：
- mp4 视频
- 1-3 张关键帧截图
- 风险片段起止时间
- 实体列表
- 关系列表
- 一段自然语言解释
- 处置建议
