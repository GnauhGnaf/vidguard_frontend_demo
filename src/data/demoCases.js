export const detectionSteps = [
  '视频与字幕输入',
  '视觉实体与动作抽取',
  '字幕上下文解析',
  '跨源语义对齐',
  '意图推理与报告生成'
]

export const demoCases = [
  {
    id: 'safe-video',
    title: '合规样本',
    category: '视频合规 / 字幕合规',
    description: '视觉内容与字幕语义均为日常场景，组合后不产生隐含风险。',
    video: '/demo-data/videos/demo-safe.mp4',
    subtitle: 'The woman drinks water using the bottle.',
    visualSignal: '视频中人物正在使用瓶子喝水，动作目标清晰，场景语义为日常行为。',
    textSignal: '字幕与画面一致，仅描述普通饮水行为，不包含诱导、攻击或隐喻性风险表达。',
    fusionSignal: '视觉证据和字幕语义相互印证，组合后仍为低风险日常场景。',
    decision: 'allowed',
    riskLevel: 'low',
    confidence: 0.9819,
    riskTypes: ['None'],
    segments: [],
    entities: [
      { id: 'woman', type: 'person', attribute: 'normal' },
      { id: 'bottle', type: 'object', attribute: 'benign' }
    ],
    relations: [
      { source: 'woman', relation: 'drink_from', target: 'bottle', risk: false },
      { source: 'subtitle', relation: 'describes', target: 'drink_action', risk: false }
    ],
    explanation: '系统从视频中识别到普通饮水行为，字幕也只是在描述该行为本身。视觉图与文本图在实体和动作层面保持一致，未产生额外隐含意图，因此判定为合规。',
    recommendation: '允许发布。'
  },
  {
    id: 'literal-risk',
    title: '显性不合规样本',
    category: '视频不合规 / 字幕不合规',
    description: '视频画面和字幕都直接表达高风险行为，属于显性不合规内容。',
    video: '/demo-data/videos/demo-harmful.mp4',
    subtitle: 'The man robs the woman using the real gun.',
    visualSignal: '视频中存在威胁性动作和危险物体，视觉内容本身已经具有明显风险。',
    textSignal: '字幕直接描述抢劫和真实枪支，明确表达不安全行为。',
    fusionSignal: '视觉证据与字幕语义方向一致，二者共同强化高风险意图判断。',
    decision: 'blocked',
    riskLevel: 'high',
    confidence: 0.9904,
    riskTypes: ['Threaten', 'Illegal Activity', 'Harassment'],
    segments: [],
    entities: [
      { id: 'man', type: 'person' },
      { id: 'woman', type: 'person' },
      { id: 'gun', type: 'weapon', attribute: 'dangerous' }
    ],
    relations: [
      { source: 'man', relation: 'rob', target: 'woman', risk: true },
      { source: 'man', relation: 'use', target: 'gun', risk: true },
      { source: 'subtitle', relation: 'explicitly_states', target: 'robbery', risk: true }
    ],
    explanation: '该样本不需要依赖隐喻推理：视频中已经呈现威胁性行为，字幕又明确描述“抢劫”和“真实枪支”。系统在视觉图与文本图中均发现高风险语义，并在跨源对齐阶段确认二者一致，因此判定为不合规。',
    recommendation: '建议直接拦截发布，并保留视频与字幕组合证据供审核留痕。'
  },
  {
    id: 'metaphor-risk',
    title: '隐喻组合不合规样本',
    category: '视频表层隐晦 / 组合不合规',
    description: '画面中的刀具接触行为与字幕上下文共同构成胁迫语义。',
    video: '/demo-data/videos/demo-metaphor.mp4',
    subtitle: 'This allows the man to supervise the woman',
    visualSignal: '视频呈现厨房场景：男性靠近并触碰桌上的刀具，女性在门口表现出紧张和恐惧。单看画面时，刀具也可能被解释为厨房物品，但人物姿态和女性反应提供了危险上下文。',
    textSignal: '字幕使用 supervise 和 object on the table 这类委婉表达，没有直接说出暴力或武器，但将“桌上物体”和“控制女性”建立了语义联系。',
    fusionSignal: '系统将视觉中的刀具、男性动作、女性恐惧反应与字幕中的控制意图对齐，推断该片段隐含“以桌上刀具施压/威胁”的不安全意图。',
    decision: 'blocked',
    riskLevel: 'high',
    confidence: 0.9637,
    riskTypes: ['Threaten', 'Harassment'],
    segments: [],
    entities: [
      { id: 'man', type: 'person' },
      { id: 'woman', type: 'person', attribute: 'fear' },
      { id: 'knife', type: 'object', attribute: 'dangerous_context' },
      { id: 'text_context', type: 'caption', attribute: 'coercive_intent' }
    ],
    relations: [
      { source: 'man', relation: 'touch', target: 'knife', risk: true },
      { source: 'woman', relation: 'shows', target: 'fear', risk: true },
      { source: 'subtitle', relation: 'reframes', target: 'knife_as_pressure_tool', risk: true },
      { source: 'man', relation: 'exert_pressure_on', target: 'woman', risk: true }
    ],
    explanation: '该样本体现“感知不够”的问题：如果只把画面理解为厨房中触碰刀具，模型可能将其视为普通生活场景；但女性的恐惧反应、男性靠近刀具的动作，以及字幕中“用桌上物体监督/控制女性”的委婉表达共同改变了语义。VidGuard 通过跨源对齐发现刀具在当前语境下不再只是普通厨具，而是被文本上下文重新解释为施压工具，因此判定视频与字幕组合不合规。',
    recommendation: '建议拦截当前视频+字幕组合；若用于合规展示，应移除控制性字幕，并避免将刀具动作与对女性施压的语义绑定。'
  }
]

export const aigcExamples = [
  {
    id: 'aigc-risk',
    prompt: '一个男人拿着刀走向一个害怕的女人，场景紧张，光线昏暗。',
    status: 'blocked',
    video: '/demo-data/videos/demo-harmful.mp4',
    confidence: 0.9542,
    riskTypes: ['威胁', '暴力暗示', '隐性危险关系'],
    graph: [
      { source: 'man', relation: 'hold', target: 'weapon', risk: true },
      { source: 'man', relation: 'approach', target: 'woman', risk: true },
      { source: 'woman', relation: 'attribute', target: 'fear', risk: true }
    ],
    explanation: '提示词中包含高风险实体和威胁性关系组合，系统推断该场景可能形成暴力或胁迫语义，因此拒绝生成或发布。',
    rewrite: '一个演员在电影拍摄现场手持道具，与工作人员共同完成安全排练，场景明确为影视制作。'
  },
  {
    id: 'aigc-safe',
    prompt: '一位女士拿着瓶子喝水，画面自然，气氛平静。',
    status: 'allowed',
    video: '/demo-data/videos/demo-safe.mp4',
    confidence: 0.9874,
    riskTypes: ['正常内容'],
    graph: [
      { source: 'woman', relation: 'drink_from', target: 'bottle', risk: false },
      { source: 'scene', relation: 'attribute', target: 'calm', risk: false }
    ],
    explanation: '提示词和生成语义中未检测到危险实体、敏感属性或高风险关系。',
    rewrite: ''
  }
]
