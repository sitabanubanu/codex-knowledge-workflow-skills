#!/usr/bin/env node
/*
Analyze large chat JSON exports into structure, stats, per-sender profiles,
samples, and cross-time evidence. Local only; no network calls.
*/

const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const key = argv[i];
    if (key.startsWith("--")) {
      args[key.slice(2)] = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : true;
    }
  }
  return args;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}

function writeJson(file, data) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
}

function toText(value) {
  if (value == null) return "";
  if (Array.isArray(value)) return value.map(toText).join(" ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function normalizeTime(value) {
  if (value == null) return null;
  if (typeof value === "number") {
    const ms = value > 1e12 ? value : value * 1000;
    const d = new Date(ms);
    return isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d;
}

function scoreKey(obj, names, type, allowFallback = true) {
  const keys = Object.keys(obj || {});
  const lower = new Map(keys.map(k => [k.toLowerCase(), k]));
  for (const name of names) {
    if (lower.has(name)) return lower.get(name);
  }
  if (!allowFallback) return null;
  return keys.find(k => type === "string" ? typeof obj[k] === "string" : typeof obj[k] === "number") || null;
}

function findMessages(data) {
  if (Array.isArray(data)) return { msgKey: "$root", messages: data };
  let best = null;
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value) && value.length > 0) {
      if (!best || value.length > best.messages.length) best = { msgKey: key, messages: value };
    }
  }
  if (!best) throw new Error("No message array found. Expected a root array or a large array field.");
  return best;
}

const STOP_WORDS = new Set("我 你 他 她 它 的 了 是 不 就 都 也 这 那 在 有 和 但 要 会 可以 能 去 来 到 上 下 里 外 把 被 让 给 对 跟 从 因为 所以 如果 虽然 然后 还是 或者 没 很 还 已经 怎么 什么 为什么 哪 谁 多少 几 一个 这个 那个 不是 就是 时候 现在 今天 明天 昨天 知道 觉得 啊 吧 吗 呢 哈 嗯 呀 哦".split(/\s+/));

const KEYWORD_GROUPS = {
  "遗憾与后悔": ["后悔", "遗憾", "可惜", "要是", "如果", "早知道", "当初", "错过", "回不去"],
  "认知转变": ["原来", "才知道", "才发现", "才明白", "意识到", "突然明白", "突然发现"],
  "自我反思": ["我觉得我", "我发现我", "我感觉我", "我这个人", "我的问题", "我太", "我还不够"],
  "放弃与妥协": ["算了", "不说了", "就这样吧", "随便吧", "无所谓了", "累了", "不想了"],
  "孤独与失落": ["一个人", "没人", "不回", "不理", "冷落", "忽视", "不在乎"],
  "愤怒与不满": ["凭什么", "不公平", "为什么我", "他妈", "操", "恶心", "气死"],
  "渴望与期待": ["希望", "想要", "如果有一天", "将来", "以后", "总有一天"],
  "关系不安": ["你是不是", "你为什么不", "你怎么不", "你不回我", "你在哪", "别不理我"]
};

const EMOTION_CUES = ["难过", "烦", "烦死", "累", "崩", "破防", "委屈", "生气", "想哭", "不开心", "痛苦", "焦虑", "孤独", "失望", "害怕", "慌", "气死", "emo"];
const ANALYSIS_CUES = ["因为", "所以", "本质", "逻辑", "问题", "原因", "分析", "其实", "我觉得", "我发现", "意味着", "归根到底", "核心", "证据", "判断", "复盘"];
const SELF_MOCKERY_CUES = ["我真是", "我就是", "我太菜", "我好废", "我不配", "我傻", "我蠢", "我有病", "废物", "垃圾", "小丑", "笑死我", "我太"];
const PING_CUES = ["在吗", "回我", "看到回", "你在不在", "怎么不回", "别不理我"];
const CONFLICT_CUES = ["凭什么", "不公平", "算了", "不说了", "随便", "不同意", "不一样", "争", "吵", "吵架", "烦", "恶心", "生气", "委屈", "不想理"];
const PRINCIPLE_PATTERNS = [
  { name: "conditional_rule", matched: "你可以X，但/只要Y，就Z", regex: /(你可以|可以).{1,50}(但|但是|只要).{1,100}(就|会|都会)/ },
  { name: "redefinition", matched: "X不是Y，X是Z", regex: /(.{1,40})(不是|并不是)(.{1,40})(而是|是)(.{1,100})/ },
  { name: "argument", matched: "我认为X，因为Y", regex: /(我认为|我觉得|我发现|我相信).{1,100}(因为|原因|所以)/ },
  { name: "attribution_reframe", matched: "不是X的问题，是Y的问题", regex: /(不是|并不是).{1,70}(问题|原因).{0,20}(是|而是).{1,100}/ },
  { name: "belief_reversal", matched: "我以前以为X，但后来Y", regex: /(我以前|以前|之前).{0,30}(以为|认为|觉得).{1,100}(但|但是|后来|现在|才发现|才知道|才明白)/ },
  { name: "essence_claim", matched: "本质/核心问题是X", regex: /(本质上|归根到底|核心问题|说到底|本质|核心).{0,100}(是|在于)/ }
];

const TOPIC_DOMAINS = {
  self: ["我这个人", "我的问题", "我觉得我", "自我", "废物", "天赋", "成长", "反思", "不甘"],
  relationship: ["朋友", "恋爱", "喜欢", "爱", "关系", "你怎么", "在乎", "陪", "不回", "对象"],
  money: ["钱", "交易", "股票", "币", "投资", "市场", "亏", "赚", "资本", "爆仓"],
  schoolCareer: ["学校", "双非", "专业", "土木", "考研", "学习", "就业", "实习", "导师"],
  societyLaw: ["法律", "制度", "社会", "政治", "国家", "程序正义", "资本", "阶级", "公平"],
  future: ["未来", "以后", "将来", "出路", "改变", "规划", "目标", "方向"],
  bodyDiscipline: ["睡眠", "失眠", "多巴胺", "戒断", "欲望", "身体", "自律", "糖", "游戏"],
  creationTech: ["AI", "agent", "代码", "编程", "项目", "skill", "产品", "工具", "部署"]
};

function includesAny(text, cues) {
  return cues.some(cue => text.includes(cue));
}

function hasQuestion(text) {
  return /[?？]/.test(text) || ["为什么", "怎么", "是不是", "能不能", "可不可以", "在吗", "对吗", "行不行"].some(cue => text.includes(cue));
}

function hasPing(text) {
  return /@[\w\u4e00-\u9fa5_-]{1,30}/.test(text) || includesAny(text, PING_CUES);
}

function minutesBetween(a, b) {
  return Math.round((b.timestamp - a.timestamp) / 60000);
}

function compactEvidence(message, extra = {}) {
  return {
    index: message.index,
    date: message.date,
    datetime: message.datetime,
    sender: message.sender,
    content: message.content.slice(0, 500),
    ...extra
  };
}

function addPattern(patterns, sender, type, event) {
  patterns[sender] ||= {};
  patterns[sender][type] ||= [];
  if (patterns[sender][type].length < 80) patterns[sender][type].push(event);
}

function summarizePatterns(patterns) {
  const summary = {};
  for (const [sender, byType] of Object.entries(patterns)) {
    summary[sender] = {};
    for (const [type, events] of Object.entries(byType)) {
      const months = [...new Set(events.flatMap(event => {
        const values = [];
        for (const item of Object.values(event)) {
          if (item && typeof item === "object" && item.date) values.push(item.date.slice(0, 7));
        }
        return values;
      }))];
      summary[sender][type] = {
        count: events.length,
        uniqueMonths: months.length,
        status: months.length >= 3 ? "High" : months.length >= 2 ? "Medium" : events.length >= 2 ? "Low" : "Insufficient"
      };
    }
  }
  return summary;
}

function detectBehaviorPatterns(messages) {
  const sorted = [...messages].sort((a, b) => a.timestamp - b.timestamp);
  const patterns = {};

  for (let i = 0; i < sorted.length; i++) {
    const current = sorted[i];
    const text = current.content || "";
    const next = sorted[i + 1] || null;
    const nextSame = sorted.slice(i + 1, Math.min(sorted.length, i + 25)).find(m => m.sender === current.sender);

    if (
      text.length > 0 &&
      text.length <= 60 &&
      includesAny(text, EMOTION_CUES) &&
      nextSame &&
      minutesBetween(current, nextSame) >= 0 &&
      minutesBetween(current, nextSame) <= 180 &&
      nextSame.content.length >= 150 &&
      includesAny(nextSame.content, ANALYSIS_CUES)
    ) {
      addPattern(patterns, current.sender, "emotional_to_analytical", {
        shortEmotion: compactEvidence(current),
        laterAnalysis: compactEvidence(nextSame, { minutesLater: minutesBetween(current, nextSame) })
      });
    }

    if (includesAny(text, SELF_MOCKERY_CUES) && nextSame) {
      const gapMinutes = minutesBetween(current, nextSame);
      if (gapMinutes >= 360) {
        addPattern(patterns, current.sender, "self_mockery_then_silence", {
          selfMockery: compactEvidence(current),
          nextOwnMessage: compactEvidence(nextSame, { silenceMinutes: gapMinutes })
        });
      }
    }

    if ((hasPing(text) || hasQuestion(text)) && next) {
      const responseWindowMinutes = 60;
      const hasOtherResponse = sorted
        .slice(i + 1, Math.min(sorted.length, i + 30))
        .some(m => m.sender !== current.sender && minutesBetween(current, m) >= 0 && minutesBetween(current, m) <= responseWindowMinutes);
      const nextOwnWithinSixHours = nextSame && minutesBetween(current, nextSame) > 0 && minutesBetween(current, nextSame) <= 360;
      if (!hasOtherResponse && nextOwnWithinSixHours) {
        addPattern(patterns, current.sender, "question_or_ping_without_quick_response", {
          questionOrPing: compactEvidence(current),
          nextOwnMessage: compactEvidence(nextSame, { minutesLater: minutesBetween(current, nextSame) })
        });
      }
    }

    if (
      includesAny(text, CONFLICT_CUES) &&
      nextSame &&
      minutesBetween(current, nextSame) >= 0 &&
      minutesBetween(current, nextSame) <= 180 &&
      nextSame.content.length >= 150 &&
      includesAny(nextSame.content, ANALYSIS_CUES)
    ) {
      addPattern(patterns, current.sender, "long_rationalization_after_conflict", {
        conflictCue: compactEvidence(current),
        laterRationalization: compactEvidence(nextSame, { minutesLater: minutesBetween(current, nextSame) })
      });
    }
  }

  return {
    note: "Behavior patterns are heuristic sequence evidence, not conclusions. Use them as leads and verify with quotes, dates, and repetition.",
    patternsBySender: patterns,
    summary: summarizePatterns(patterns)
  };
}

function matchPrincipleStatement(text) {
  if (!text || text.length < 60) return null;
  for (const pattern of PRINCIPLE_PATTERNS) {
    if (pattern.regex.test(text)) {
      return { pattern: pattern.name, matched: pattern.matched };
    }
  }
  return null;
}

function detectPrincipleStatements(messages) {
  const statementsBySender = {};
  const patternCountsBySender = {};

  for (const message of messages) {
    const text = message.content || "";
    const match = matchPrincipleStatement(text);
    if (!match) continue;
    const item = {
      index: message.index,
      date: message.date,
      datetime: message.datetime,
      sender: message.sender,
      pattern: match.pattern,
      matched: match.matched,
      content: text.slice(0, 700)
    };
    statementsBySender[message.sender] ||= [];
    patternCountsBySender[message.sender] ||= {};
    if (statementsBySender[message.sender].length < 180) statementsBySender[message.sender].push(item);
    patternCountsBySender[message.sender][match.pattern] = (patternCountsBySender[message.sender][match.pattern] || 0) + 1;
  }

  const summary = {};
  for (const [sender, statements] of Object.entries(statementsBySender)) {
    const months = new Set(statements.map(item => item.date.slice(0, 7)));
    summary[sender] = {
      total: statements.length,
      uniqueMonths: months.size,
      patterns: patternCountsBySender[sender] || {}
    };
  }

  return {
    note: "Heuristic sentence-structure matches. Use as principle-statement fuel for Core Thread Burn, not as final conclusions.",
    statementsBySender,
    summary
  };
}

function weekStart(date) {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() - day + 1);
  return d;
}

function classifyTopicDomains(text) {
  const domains = [];
  for (const [domain, cues] of Object.entries(TOPIC_DOMAINS)) {
    if (includesAny(text, cues)) domains.push(domain);
  }
  return domains;
}

function detectCognitiveBreakWindows(messages, principleStatements) {
  const principleIndexes = new Set();
  for (const statements of Object.values(principleStatements.statementsBySender || {})) {
    for (const item of statements) principleIndexes.add(item.index);
  }

  const windowsByKey = {};
  for (const message of messages) {
    const text = message.content || "";
    const domains = classifyTopicDomains(text);
    const isLong = text.length > 100;
    const hasPrinciple = principleIndexes.has(message.index);
    if (!isLong && !hasPrinciple) continue;

    const start = weekStart(new Date(message.timestamp));
    const end = new Date(start);
    end.setUTCDate(end.getUTCDate() + 6);
    const weekKey = start.toISOString().slice(0, 10);
    const key = `${message.sender}::${weekKey}`;
    windowsByKey[key] ||= {
      weekStart: weekKey,
      weekEnd: end.toISOString().slice(0, 10),
      sender: message.sender,
      longMessageCount: 0,
      principleStatementCount: 0,
      topicDomains: new Set(),
      coreQuotes: []
    };
    const window = windowsByKey[key];
    if (isLong) window.longMessageCount += 1;
    if (hasPrinciple) window.principleStatementCount += 1;
    for (const domain of domains) window.topicDomains.add(domain);
    if (window.coreQuotes.length < 5 && (isLong || hasPrinciple)) {
      window.coreQuotes.push(compactEvidence(message, { domains, principleStatement: hasPrinciple }));
    }
  }

  const windows = Object.values(windowsByKey).map(window => {
    const topicDomains = [...window.topicDomains].sort();
    let status = "context_window";
    if (window.longMessageCount >= 3 && topicDomains.length >= 3 && window.principleStatementCount >= 1) {
      status = "suspected_cognitive_break";
    } else if (window.longMessageCount >= 5 && window.principleStatementCount >= 2) {
      status = "intense_single_or_narrow_domain_window";
    }
    return {
      weekStart: window.weekStart,
      weekEnd: window.weekEnd,
      sender: window.sender,
      longMessageCount: window.longMessageCount,
      principleStatementCount: window.principleStatementCount,
      topicDomains,
      status,
      coreQuotes: window.coreQuotes
    };
  }).filter(window => window.status !== "context_window")
    .sort((a, b) => {
      const scoreA = a.longMessageCount + a.principleStatementCount * 2 + a.topicDomains.length;
      const scoreB = b.longMessageCount + b.principleStatementCount * 2 + b.topicDomains.length;
      return scoreB - scoreA || a.weekStart.localeCompare(b.weekStart);
    });

  return {
    note: "Candidate cognitive restructuring windows. Verify manually; these are not conclusions.",
    windows
  };
}

const TENSION_ADMISSION_CUES = ["其实我", "说实话", "说真的", "老实说", "坦白说", "我自己反而", "我承认", "我发现我", "我知道我", "我其实", "我也会", "我反而"];
const TENSION_NEGATIVE_CUES = ["不是", "并不是", "不能", "不会", "不该", "不需要", "不要", "别", "没用", "没有意义", "不重要", "不值得", "放屁", "扯淡", "否定", "不信", "拒绝", "假的", "虚伪"];
const TENSION_POSITIVE_CUES = ["应该", "需要", "值得", "重要", "必须", "可以", "想要", "在乎", "承认", "喜欢", "希望", "相信", "接受", "改变", "做到"];
const TENSION_EXTRA_DOMAINS = {
  self: ["爱自己", "自尊", "自信", "自卑", "锚点", "存在", "痕迹", "价值感", "我自己", "自我"],
  relationship: ["走心", "亲密", "喜欢", "在乎", "被爱", "陪伴", "朋友", "回应", "不回", "冷落"],
  schoolCareer: ["成绩", "排名", "班级第一", "学习委员", "奖学金", "绩点", "保研", "考学", "考研"],
  bodyDiscipline: ["戒断", "上瘾", "控制", "失控", "配额", "打分", "反向记分", "清单"],
  creationTech: ["工具", "工作流", "工程化", "agent", "AI", "skill", "项目"],
  future: ["出路", "命运", "改变命", "阶层", "未来", "规划"],
  societyLaw: ["制度", "公平", "正义", "法律", "社会", "政治"]
};
const TENSION_TYPE_PRIORITY = {
  long_denial_to_admission: 6,
  principle_vs_behavior: 5,
  stance_reversal: 3
};
const TENSION_CONFIDENCE_SCORE = { High: 3, Medium: 2, Low: 1, Insufficient: 0 };

function uniqueValues(values) {
  return [...new Set(values.filter(Boolean))];
}

function classifyTensionDomains(text) {
  const domains = new Set(classifyTopicDomains(text || ""));
  for (const [domain, cues] of Object.entries(TENSION_EXTRA_DOMAINS)) {
    if (includesAny(text || "", cues)) domains.add(domain);
  }
  return [...domains].sort();
}

function overlapsAny(a, b) {
  const bSet = new Set(b || []);
  return (a || []).some(item => bSet.has(item));
}

function tensionStance(text) {
  const hasAdmission = includesAny(text || "", TENSION_ADMISSION_CUES);
  const hasNegative = includesAny(text || "", TENSION_NEGATIVE_CUES);
  const hasPositive = includesAny(text || "", TENSION_POSITIVE_CUES);
  if (hasAdmission) return "admission";
  if (hasNegative && hasPositive) return "mixed";
  if (hasNegative) return "negative";
  if (hasPositive) return "positive";
  return "unknown";
}

function opposingStance(a, b) {
  const left = new Set(["negative"]);
  const right = new Set(["positive", "admission"]);
  return (left.has(a) && right.has(b)) || (right.has(a) && left.has(b));
}

function statementTimestamp(statement, messageByIndex) {
  const original = messageByIndex.get(statement.index);
  if (original) return original.timestamp;
  const parsed = Date.parse(statement.datetime || statement.date || "");
  return Number.isFinite(parsed) ? parsed : 0;
}

function compactStatement(statement, messageByIndex, extra = {}) {
  const original = messageByIndex.get(statement.index);
  return {
    source: statement.source || "principle_statements",
    index: statement.index,
    date: statement.date,
    datetime: statement.datetime,
    pattern: statement.pattern,
    content: (statement.content || original?.content || "").slice(0, 500),
    ...extra
  };
}

function buildTensionStatements(messages, principleStatements) {
  const statementsBySender = {};
  const seenIndexes = new Set();
  for (const [sender, statements] of Object.entries(principleStatements.statementsBySender || {})) {
    statementsBySender[sender] ||= [];
    for (const statement of statements) {
      statementsBySender[sender].push({ ...statement, source: "principle_statements" });
      seenIndexes.add(statement.index);
    }
  }

  for (const message of messages) {
    if (seenIndexes.has(message.index)) continue;
    const text = message.content || "";
    if (text.length < 20) continue;
    const domains = classifyTensionDomains(text);
    const stance = tensionStance(text);
    if (domains.length === 0 || stance === "unknown" || stance === "mixed") continue;
    statementsBySender[message.sender] ||= [];
    statementsBySender[message.sender].push({
      index: message.index,
      date: message.date,
      datetime: message.datetime,
      sender: message.sender,
      pattern: "tension_cue_fallback",
      matched: "domain + stance cue",
      source: "normalized_messages",
      content: text.slice(0, 700)
    });
  }

  for (const statements of Object.values(statementsBySender)) {
    statements.sort((a, b) => (a.index || 0) - (b.index || 0));
  }

  return statementsBySender;
}

function dateRangeFromEvidence(items) {
  const dates = items.map(item => item.date).filter(Boolean).sort();
  if (dates.length === 0) return null;
  return dates.length === 1 ? dates[0] : `${dates[0]} to ${dates[dates.length - 1]}`;
}

function confidenceFromEvidence(count, uniqueMonths, base = "Low") {
  if (count >= 5 && uniqueMonths >= 2) return "High";
  if (count >= 3 || uniqueMonths >= 2) return "Medium";
  if (count >= 2) return base;
  return "Insufficient";
}

function addTension(tensionsBySender, sender, tension) {
  tensionsBySender[sender] ||= [];
  tensionsBySender[sender].push(tension);
}

function buildTensionSummary(contradictionsBySender) {
  const summary = {
    totalContradictions: 0,
    byType: {},
    byConfidence: {},
    bySender: {}
  };
  for (const [sender, tensions] of Object.entries(contradictionsBySender)) {
    summary.bySender[sender] = tensions.length;
    summary.totalContradictions += tensions.length;
    for (const tension of tensions) {
      summary.byType[tension.type] = (summary.byType[tension.type] || 0) + 1;
      summary.byConfidence[tension.confidence] = (summary.byConfidence[tension.confidence] || 0) + 1;
    }
  }
  return summary;
}

function detectStructuralTensions(messages, principleStatements, behaviorPatterns) {
  const messageByIndex = new Map(messages.map(message => [message.index, message]));
  const messagesBySender = {};
  for (const message of messages) {
    messagesBySender[message.sender] ||= [];
    messagesBySender[message.sender].push(message);
  }
  for (const senderMessages of Object.values(messagesBySender)) {
    senderMessages.sort((a, b) => a.timestamp - b.timestamp);
  }

  const contradictionsBySender = {};
  const statementsBySender = buildTensionStatements(messages, principleStatements);
  const ninetyDays = 90 * 24 * 60 * 60 * 1000;
  const oneYear = 365 * 24 * 60 * 60 * 1000;
  const sixtyDays = 60 * 24 * 60 * 60 * 1000;

  for (const [sender, statementsRaw] of Object.entries(statementsBySender)) {
    const statements = [...statementsRaw].sort((a, b) => statementTimestamp(a, messageByIndex) - statementTimestamp(b, messageByIndex));
    const senderMessages = messagesBySender[sender] || [];

    for (const statement of statements) {
      const text = statement.content || "";
      const domains = classifyTensionDomains(text);
      const stance = tensionStance(text);
      if (domains.length === 0 || stance !== "negative") continue;
      const start = statementTimestamp(statement, messageByIndex);
      const end = start + ninetyDays;
      const laterOccurrences = senderMessages
        .filter(message => message.index !== statement.index && message.timestamp > start && message.timestamp <= end)
        .map(message => ({ message, domains: classifyTensionDomains(message.content || "") }))
        .filter(item => overlapsAny(domains, item.domains))
        .slice(0, 12);
      if (laterOccurrences.length < 2) continue;
      const months = uniqueValues(laterOccurrences.map(item => item.message.date.slice(0, 7)));
      const confidence = confidenceFromEvidence(laterOccurrences.length, months.length);
      const evidence = laterOccurrences.slice(0, 5).map(item => compactEvidence(item.message, { topicDomains: item.domains }));
      addTension(contradictionsBySender, sender, {
        type: "principle_vs_behavior",
        detectorType: "Type 1",
        status: "tensionCandidate",
        confidence,
        rankScore: 5000 + TENSION_CONFIDENCE_SCORE[confidence] * 100 + laterOccurrences.length,
        poleA: compactStatement(statement, messageByIndex, { stance, topicDomains: domains }),
        poleB: {
          source: "normalized_messages",
          dateRange: dateRangeFromEvidence(evidence),
          occurrences: laterOccurrences.length,
          uniqueMonths: months.length,
          topicDomains: uniqueValues(laterOccurrences.flatMap(item => item.domains)),
          evidence
        },
        tensionDescription: "A principle-like statement rejects or negates a domain, but later same-domain behavior/discussion keeps appearing. Treat this as a structural tension candidate, not a verdict."
      });
    }

    for (const current of senderMessages) {
      const text = current.content || "";
      if (!includesAny(text, TENSION_ADMISSION_CUES) || !text.includes("我")) continue;
      const domains = classifyTensionDomains(text);
      if (domains.length === 0) continue;
      const previousDenials = statements
        .filter(statement => {
          const ts = statementTimestamp(statement, messageByIndex);
          if (ts >= current.timestamp || current.timestamp - ts > oneYear) return false;
          const statementDomains = classifyTensionDomains(statement.content || "");
          return overlapsAny(domains, statementDomains) && tensionStance(statement.content || "") === "negative";
        })
        .slice(-8);
      if (previousDenials.length < 2) continue;
      const denialEvidence = previousDenials.map(item => compactStatement(item, messageByIndex, {
        stance: "negative",
        topicDomains: classifyTensionDomains(item.content || "")
      }));
      const months = uniqueValues(denialEvidence.map(item => item.date?.slice(0, 7)));
      const confidence = previousDenials.length >= 3 || months.length >= 2 ? "High" : "Medium";
      addTension(contradictionsBySender, sender, {
        type: "long_denial_to_admission",
        detectorType: "Type 6",
        status: "tensionCandidate",
        confidence,
        rankScore: 6000 + TENSION_CONFIDENCE_SCORE[confidence] * 100 + previousDenials.length,
        poleA: {
          source: "tension_statements",
          dateRange: dateRangeFromEvidence(denialEvidence),
          occurrences: previousDenials.length,
          topicDomains: uniqueValues(denialEvidence.flatMap(item => item.topicDomains || [])),
          sourceTypes: uniqueValues(denialEvidence.map(item => item.source)),
          evidence: denialEvidence.slice(0, 5)
        },
        poleB: {
          source: "normalized_messages",
          date: current.date,
          datetime: current.datetime,
          index: current.index,
          stance: "admission",
          topicDomains: domains,
          content: text.slice(0, 500)
        },
        tensionDescription: "Earlier same-domain statements repeatedly negate or reject something; a later self-directed admission leaks the opposite need or fact. This is a high-value burn input, not a final diagnosis."
      });
    }

    for (let i = 0; i < statements.length; i++) {
      const earlier = statements[i];
      const earlierDomains = classifyTensionDomains(earlier.content || "");
      const earlierStance = tensionStance(earlier.content || "");
      if (earlierDomains.length === 0 || !["negative", "positive", "admission"].includes(earlierStance)) continue;
      for (let j = i + 1; j < statements.length; j++) {
        const later = statements[j];
        const gap = statementTimestamp(later, messageByIndex) - statementTimestamp(earlier, messageByIndex);
        if (gap < sixtyDays) continue;
        const laterDomains = classifyTensionDomains(later.content || "");
        const laterStance = tensionStance(later.content || "");
        if (!overlapsAny(earlierDomains, laterDomains) || !opposingStance(earlierStance, laterStance)) continue;
        const confidence = gap >= oneYear ? "Medium" : "Low";
        addTension(contradictionsBySender, sender, {
          type: "stance_reversal",
          detectorType: "Type 5",
          status: "tensionCandidate",
          confidence,
          rankScore: 3000 + TENSION_CONFIDENCE_SCORE[confidence] * 100 + Math.round(gap / (30 * 24 * 60 * 60 * 1000)),
          poleA: compactStatement(earlier, messageByIndex, { stance: earlierStance, topicDomains: earlierDomains }),
          poleB: compactStatement(later, messageByIndex, { stance: laterStance, topicDomains: laterDomains }),
          tensionDescription: "The same speaker appears to reverse stance in the same domain across time. Verify manually; this may be growth, context change, irony, or a real tension."
        });
      }
    }
  }

  for (const [sender, tensions] of Object.entries(contradictionsBySender)) {
    tensions.sort((a, b) => b.rankScore - a.rankScore || (a.poleA.date || "").localeCompare(b.poleA.date || ""));
    contradictionsBySender[sender] = tensions.slice(0, 40).map((tension, index) => ({
      tensionId: `T${String(index + 1).padStart(3, "0")}`,
      ...tension,
      burnPriority: index + 1
    }));
  }

  return {
    note: "Structural tension candidates. These are ranked leads for Core Thread Burn, not proof that a person is inconsistent or hypocritical.",
    priorityOrder: ["long_denial_to_admission", "principle_vs_behavior", "stance_reversal"],
    generatedFrom: ["principle_statements.json", "behavior_patterns.json", "_normalized/messages.json"],
    behaviorPatternSummaryAvailable: Boolean(behaviorPatterns && behaviorPatterns.summary),
    contradictionsBySender,
    summary: buildTensionSummary(contradictionsBySender)
  };
}

const METADATA_STOP_WORDS = new Set([
  "回复", "引用消息", "聊天记录", "群聊的聊天记录", "的聊天记录",
  "文件", "链接", "图片", "视频", "表情", "动画表情", "语音",
  "系统消息", "撤回了一条消息", "你撤回了一条消息", "位置共享已经结束",
  "语音通话已经结束", "发起转账", "领取了你的", "转账", "红包", "所有人", "CDATA", "link",
  "type", "plain", "username", "template", "sysmsgtemplate", "memberlist",
  "member", "nickname", "profile", "sysmsg", "content", "name", "remark",
  "wxid", "custom", "SystemMessages", "HongbaoIcon", "opendetail", "https",
  "http", "min"
]);

function topWords(messages, contentKey, topN = 40, extraStopWords = new Set()) {
  const counts = {};
  for (const m of messages) {
    const text = toText(m[contentKey]);
    const tokens = text.match(/[\u4e00-\u9fa5]{2,}|[A-Za-z]{3,}/g) || [];
    for (const token of tokens) {
      if (STOP_WORDS.has(token)) continue;
      if (METADATA_STOP_WORDS.has(token)) continue;
      if (extraStopWords.has(token)) continue;
      counts[token] = (counts[token] || 0) + 1;
    }
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, topN);
}

function cleanAlias(value) {
  return toText(value)
    .replace(/[\u2005\u2006\u2009\u200a\u200b]/g, "")
    .replace(/^[@\s"'“”‘’.,，。:：；;、\[\]【】()（）<>《》]+|[@\s"'“”‘’.,，。:：；;、\[\]【】()（）<>《》]+$/g, "")
    .trim()
    .slice(0, 60);
}

function isValidAliasName(value) {
  const alias = cleanAlias(value);
  if (!alias || alias.length < 2) return false;
  if (/^\d+$/.test(alias)) return false;
  if (/^(我|你|他|她|它|了|所有人|all)$/i.test(alias)) return false;
  if (/^(的)?聊天记录$/.test(alias)) return false;
  if (/^(https?|www|com|cn|jpg|png|gif|mp4|min)$/i.test(alias)) return false;
  return /[\u4e00-\u9fa5A-Za-z]/.test(alias);
}

function addLimited(list, item, limit = 20) {
  if (list.length < limit) list.push(item);
}

function parseIdentityMap(value) {
  if (!value) return {};
  let raw = value;
  if (fs.existsSync(value)) raw = fs.readFileSync(value, "utf8");
  try {
    const parsed = JSON.parse(raw);
    const out = {};
    const participants = parsed.humanParticipants || parsed.participants || [];
    if (Array.isArray(participants)) {
      for (const p of participants) {
        const canonical = p.canonical || p.canonicalSender || p.sender || p.name;
        if (!canonical) continue;
        out[canonical] = Array.isArray(p.aliases) ? p.aliases.map(cleanAlias).filter(Boolean) : [];
      }
    } else {
      for (const [sender, aliases] of Object.entries(parsed)) {
        out[sender] = Array.isArray(aliases) ? aliases.map(cleanAlias).filter(Boolean) : [];
      }
    }
    return out;
  } catch (_) {
    const out = {};
    for (const part of raw.split(";")) {
      const [sender, aliasText] = part.split(/[:=]/);
      if (!sender || !aliasText) continue;
      out[cleanAlias(sender)] = aliasText.split("|").map(cleanAlias).filter(Boolean);
    }
    return out;
  }
}

function summarizeSenderTypes(messages) {
  const bySender = {};
  for (const m of messages) {
    bySender[m.sender] ||= {};
    bySender[m.sender][m.type || ""] = (bySender[m.sender][m.type || ""] || 0) + 1;
  }
  return bySender;
}

function looksNonHumanSender(sender, total, typeCounts) {
  const systemCount = typeCounts.system || 0;
  const nonTextCount = Object.entries(typeCounts)
    .filter(([type]) => type && type !== "text" && type !== "")
    .reduce((sum, [, count]) => sum + count, 0);
  const systemRatio = systemCount / Math.max(total, 1);
  const nonTextRatio = nonTextCount / Math.max(total, 1);
  return (
    !cleanAlias(sender) ||
    cleanAlias(sender) === "(空)" ||
    cleanAlias(sender).includes("空") ||
    systemRatio >= 0.95 ||
    (total <= 20 && nonTextRatio >= 0.8)
  );
}

function buildParticipantMap(messages, senderCount, targetAliases = [], identityMapValue = null) {
  const typeCountsBySender = summarizeSenderTypes(messages);
  const providedIdentityMap = parseIdentityMap(identityMapValue);
  const participants = [];
  const nonHumanBuckets = [];
  const humanSenderNames = new Set();

  for (const [sender, count] of Object.entries(senderCount)) {
    const typeCounts = typeCountsBySender[sender] || {};
    if (looksNonHumanSender(sender, count, typeCounts)) {
      nonHumanBuckets.push({
        sender,
        count,
        typeCounts,
        classification: "non_human_or_system",
        reason: sender.includes("空") ? "missing sender / system-media event bucket" : "system or group-event bucket"
      });
    } else {
      humanSenderNames.add(sender);
      participants.push({
        canonicalSender: sender,
        count,
        typeCounts,
        role: "participant",
        confirmedAliases: providedIdentityMap[sender] || [],
        aliasCandidates: [],
        outgoingMentions: [],
        evidence: []
      });
    }
  }

  const participantBySender = Object.fromEntries(participants.map(p => [p.canonicalSender, p]));
  const targetSet = new Set(targetAliases.map(cleanAlias).filter(Boolean));
  for (const p of participants) {
    if (p.canonicalSender === "me" || targetSet.has(p.canonicalSender) || p.confirmedAliases.some(a => targetSet.has(a))) {
      p.role = "target_or_self_candidate";
    }
  }

  const mentionCounts = {};
  const systemActorCounts = {};
  const forwardedNameCountsBySender = {};
  const unresolvedNames = {};

  function addUnresolved(name, source, m) {
    const alias = cleanAlias(name);
    if (!isValidAliasName(alias) || humanSenderNames.has(alias)) return;
    unresolvedNames[alias] ||= { name: alias, count: 0, sources: {}, evidence: [] };
    unresolvedNames[alias].count += 1;
    unresolvedNames[alias].sources[source] = (unresolvedNames[alias].sources[source] || 0) + 1;
    addLimited(unresolvedNames[alias].evidence, compactEvidence(m, { source }), 8);
  }

  for (const m of messages) {
    const text = m.content || "";
    const senderParticipant = participantBySender[m.sender];

    for (const match of text.matchAll(/@([^\s@，,。:：；;]+)\s*/g)) {
      const alias = cleanAlias(match[1]);
      if (!isValidAliasName(alias) || humanSenderNames.has(alias)) continue;
      mentionCounts[alias] ||= { name: alias, count: 0, byMentioningSender: {}, evidence: [] };
      mentionCounts[alias].count += 1;
      mentionCounts[alias].byMentioningSender[m.sender] = (mentionCounts[alias].byMentioningSender[m.sender] || 0) + 1;
      addLimited(mentionCounts[alias].evidence, compactEvidence(m, { source: "at_mention" }), 8);
      if (senderParticipant) {
        const existing = senderParticipant.outgoingMentions.find(x => x.name === alias);
        if (existing) existing.count += 1;
        else senderParticipant.outgoingMentions.push({ name: alias, count: 1 });
      }
    }

    for (const match of text.matchAll(/"([^"\n]{1,40})"\s*撤回了一条消息/g)) {
      const alias = cleanAlias(match[1]);
      systemActorCounts[alias] = (systemActorCounts[alias] || 0) + 1;
      addUnresolved(alias, "system_recall_actor", m);
    }

    for (const match of text.matchAll(/<nickname><!\[CDATA\[([^\]]{1,60})\]\]><\/nickname>/g)) {
      addUnresolved(match[1], "system_xml_nickname", m);
    }

    for (const match of text.matchAll(/^\s*\[\d+\]\s+\d{4}[-/]\d{1,2}[-/]\d{1,2}[^\n:：]{0,40}\s+([^:\n：]{1,40})[:：]/gm)) {
      const alias = cleanAlias(match[1]);
      if (!isValidAliasName(alias) || humanSenderNames.has(alias)) continue;
      forwardedNameCountsBySender[m.sender] ||= {};
      forwardedNameCountsBySender[m.sender][alias] = (forwardedNameCountsBySender[m.sender][alias] || 0) + 1;
      addUnresolved(alias, "forwarded_chat_speaker", m);
    }

    for (const match of text.matchAll(/([^\s\n]{1,30})与([^\s\n]{1,30})的聊天记录/g)) {
      addUnresolved(match[1], "forwarded_chat_title", m);
      addUnresolved(match[2], "forwarded_chat_title", m);
    }
  }

  for (const [sender, counts] of Object.entries(forwardedNameCountsBySender)) {
    const p = participantBySender[sender];
    if (!p) continue;
    for (const [alias, count] of Object.entries(counts)) {
      if (count < 2 || p.confirmedAliases.includes(alias)) continue;
      p.aliasCandidates.push({
        name: alias,
        confidence: count >= 5 ? "Likely" : "Weak",
        reason: "appears as a forwarded-chat speaker in messages sent from this sender; verify before treating as the same person",
        count
      });
    }
  }

  const aliasStopWords = new Set([
    ...Object.keys(mentionCounts),
    ...Object.keys(systemActorCounts),
    ...Object.keys(unresolvedNames),
    ...participants.flatMap(p => [p.canonicalSender, ...p.confirmedAliases, ...p.aliasCandidates.map(a => a.name)]),
    ...nonHumanBuckets.map(b => b.sender)
  ].map(cleanAlias).filter(Boolean));

  return {
    version: 1,
    status: Object.keys(providedIdentityMap).length ? "provided_identity_map_applied" : "candidate_map_needs_confirmation",
    note: "Human participants are canonical sender buckets. Alias candidates are evidence leads, not final identity claims until confirmed.",
    rawSenderBuckets: Object.entries(senderCount).map(([sender, count]) => ({
      sender,
      count,
      typeCounts: typeCountsBySender[sender] || {}
    })),
    humanParticipants: participants,
    nonHumanBuckets,
    aliasSignals: {
      mentions: Object.values(mentionCounts).sort((a, b) => b.count - a.count).slice(0, 80),
      systemActors: Object.entries(systemActorCounts).sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count })),
      unresolvedNames: Object.values(unresolvedNames).sort((a, b) => b.count - a.count).slice(0, 120)
    },
    excludedFromPersonCount: nonHumanBuckets.map(b => b.sender),
    excludedFromTopWords: [...aliasStopWords],
    requiredInterpretationRule: "Before deep analysis, confirm humanParticipants and alias mapping. Do not count nonHumanBuckets, @mentions, forwarded-chat names, or group/system buckets as separate people."
  };
}

function monthKey(date) {
  return date.toISOString().slice(0, 7);
}

function safeName(name) {
  return String(name || "unknown").replace(/[\/\\:*?"<>|]/g, "_").slice(0, 120);
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.input) {
    console.error("Usage: node analyze_chat.js --input chat.json [--out out_dir] [--target alias1,alias2]");
    process.exit(1);
  }

  const inputPath = path.resolve(args.input);
  const baseOut = path.resolve(args.out || path.join(path.dirname(inputPath), "_chat_distill"));
  const normalizedDir = path.join(baseOut, "_normalized");
  const analysisDir = path.join(baseOut, "_analysis");
  const splitDir = path.join(baseOut, "_split");
  const profilesDir = path.join(baseOut, "_profiles");
  const samplesDir = path.join(baseOut, "_samples");
  const evidenceDir = path.join(baseOut, "_evidence");
  const findingsDir = path.join(baseOut, "_findings");
  const reviewDir = path.join(baseOut, "_review");
  const exportsDir = path.join(baseOut, "_exports");
  [normalizedDir, analysisDir, splitDir, profilesDir, samplesDir, evidenceDir, findingsDir, reviewDir, exportsDir].forEach(ensureDir);

  const data = readJson(inputPath);
  const { msgKey, messages } = findMessages(data);
  const first = messages.find(Boolean) || {};
  const senderKey = args.senderKey || scoreKey(first, ["sender", "from", "author", "name", "nickname", "username", "user"], "string");
  const contentKey = args.contentKey || scoreKey(first, ["content", "text", "message", "body", "msg"], "string");
  const timeKey = args.timeKey || scoreKey(first, ["timestamp", "time", "date", "datetime", "created_at", "ts"], "number");
  const typeKey = args.typeKey || scoreKey(first, ["type", "msgtype", "msg_type", "messagetype"], "string", false);
  if (!senderKey || !contentKey || !timeKey) {
    throw new Error(`Could not detect required fields. sender=${senderKey}, content=${contentKey}, time=${timeKey}`);
  }

  const senderCount = {};
  let firstDate = null;
  let lastDate = null;
  const normalized = messages.map((m, index) => {
    const date = normalizeTime(m[timeKey]) || new Date(0);
    if (!firstDate || date < firstDate) firstDate = date;
    if (!lastDate || date > lastDate) lastDate = date;
    const sender = toText(m[senderKey]) || "(空)";
    senderCount[sender] = (senderCount[sender] || 0) + 1;
    return {
      index,
      timestamp: date.getTime(),
      date: date.toISOString().slice(0, 10),
      datetime: date.toISOString().slice(0, 19).replace("T", " "),
      sender,
      content: toText(m[contentKey]),
      type: typeKey ? toText(m[typeKey]) : "text"
    };
  });

  const structure = {
    inputPath,
    inputType: "native-chat-json",
    msgKey,
    senderKey,
    contentKey,
    timeKey,
    typeKey,
    totalMessages: messages.length,
    senders: senderCount,
    firstDate: firstDate ? firstDate.toISOString() : null,
    lastDate: lastDate ? lastDate.toISOString() : null,
    sampleFirst: first,
    targetAliases: args.target ? args.target.split(",").map(s => s.trim()).filter(Boolean) : []
  };
  const manifest = {
    createdAt: new Date().toISOString(),
    skill: "chat-history-self-distiller",
    runtimeStatus: "SmokeTested",
    inputPath,
    inputType: "native-chat-json",
    outputDir: baseOut,
    mode: args.mode || "orientation",
    taskRoute: args.route || "orientation",
    dataBoundary: {
      localProcessing: true,
      externalUpload: false,
      thirdPartyPrivacy: "minimize quotes unless necessary"
    },
    targetAliases: structure.targetAliases,
    parser: {
      messageArray: msgKey,
      senderKey,
      contentKey,
      timeKey,
      typeKey
    },
    analyzerOutputs: {
      participantMapAvailable: true,
      behaviorPatternsAvailable: true,
      principleStatementsAvailable: true,
      structuralTensionsAvailable: true,
      cognitiveBreakWindowsAvailable: true,
      coreThreadBurnPath: path.join(analysisDir, "core_thread_burn.md")
    }
  };
  writeJson(path.join(baseOut, "_manifest.json"), manifest);
  writeJson(path.join(normalizedDir, "messages.json"), { messages: normalized });
  writeJson(path.join(analysisDir, "structure.json"), structure);
  const participantMap = buildParticipantMap(normalized, senderCount, structure.targetAliases, args.identityMap || args.participants);
  writeJson(path.join(analysisDir, "participant_map.json"), participantMap);

  const yearlySender = {};
  const monthlySender = {};
  const senderLengths = {};
  const activeHours = {};
  for (const m of normalized) {
    const d = new Date(m.timestamp);
    const year = d.getUTCFullYear().toString();
    const month = m.date.slice(0, 7);
    yearlySender[year] ||= {};
    monthlySender[month] ||= {};
    yearlySender[year][m.sender] = (yearlySender[year][m.sender] || 0) + 1;
    monthlySender[month][m.sender] = (monthlySender[month][m.sender] || 0) + 1;
    senderLengths[m.sender] ||= { total: 0, count: 0 };
    senderLengths[m.sender].total += m.content.length;
    senderLengths[m.sender].count += 1;
    activeHours[m.sender] ||= Array(24).fill(0);
    activeHours[m.sender][d.getHours()] += 1;
  }
  const avgLengths = Object.fromEntries(Object.entries(senderLengths).map(([s, v]) => [s, Number((v.total / Math.max(v.count, 1)).toFixed(1))]));
  const stats = {
    yearlySender,
    monthlySender,
    avgMessageLength: avgLengths,
    activeHours,
    topWordsBySender: {}
  };

  const bySender = {};
  for (const m of normalized) {
    bySender[m.sender] ||= [];
    bySender[m.sender].push(m);
  }
  const behaviorPatterns = detectBehaviorPatterns(normalized);
  const principleStatements = detectPrincipleStatements(normalized);
  const cognitiveBreakWindows = detectCognitiveBreakWindows(normalized, principleStatements);
  const structuralTensions = detectStructuralTensions(normalized, principleStatements, behaviorPatterns);
  const topWordStopWords = new Set(participantMap.excludedFromTopWords || []);
  for (const [sender, msgs] of Object.entries(bySender)) {
    stats.topWordsBySender[sender] = topWords(msgs.map(x => ({ content: x.content })), "content", 30, topWordStopWords);
  }
  writeJson(path.join(analysisDir, "stats.json"), stats);
  writeJson(path.join(analysisDir, "behavior_patterns.json"), behaviorPatterns);
  writeJson(path.join(analysisDir, "principle_statements.json"), principleStatements);
  writeJson(path.join(analysisDir, "contradictions.json"), structuralTensions);
  writeJson(path.join(analysisDir, "cognitive_break_windows.json"), cognitiveBreakWindows);

  const chunkSize = Number(args.chunkSize || 10000);
  for (let i = 0; i < normalized.length; i += chunkSize) {
    writeJson(path.join(splitDir, `part_${String(i / chunkSize + 1).padStart(3, "0")}.json`), { messages: normalized.slice(i, i + chunkSize) });
  }
  writeJson(path.join(analysisDir, "split_info.json"), {
    splitDir,
    totalParts: Math.ceil(normalized.length / chunkSize),
    chunkSize,
    totalMessages: normalized.length
  });

  const senderList = [];
  for (const [sender, msgs] of Object.entries(bySender)) {
    msgs.sort((a, b) => a.timestamp - b.timestamp);
    const file = `${safeName(sender)}.json`;
    senderList.push({ name: sender, count: msgs.length, safeFileName: file });
    writeJson(path.join(profilesDir, file), {
      sender,
      totalMessages: msgs.length,
      firstDate: msgs[0]?.date || null,
      lastDate: msgs[msgs.length - 1]?.date || null,
      messages: msgs
    });
  }
  senderList.sort((a, b) => b.count - a.count);
  writeJson(path.join(profilesDir, "_sender_list.json"), { senders: senderList });

  const validation = {};
  for (const info of senderList) {
    const profile = readJson(path.join(profilesDir, info.safeFileName));
    const msgs = profile.messages;
    const byMonth = {};
    for (const m of msgs) {
      const key = m.date.slice(0, 7);
      byMonth[key] ||= [];
      if (byMonth[key].length < 20 && m.content.length > 2) byMonth[key].push(m);
    }
    const months = Object.keys(byMonth).sort();
    const quarterly = {};
    for (const key of months) {
      const month = key.slice(5, 7);
      if (["01", "04", "07", "10"].includes(month)) quarterly[key] = byMonth[key];
    }
    if (Object.keys(quarterly).length === 0) {
      for (const key of months.filter((_, i) => i % Math.max(1, Math.ceil(months.length / 8)) === 0)) quarterly[key] = byMonth[key];
    }
    const keywordHits = {};
    for (const [theme, keywords] of Object.entries(KEYWORD_GROUPS)) {
      const hits = [];
      for (const m of msgs) {
        const kw = keywords.find(k => m.content.includes(k));
        if (kw) hits.push({ date: m.date, month: m.date.slice(0, 7), keyword: kw, content: m.content.slice(0, 500) });
      }
      if (hits.length) keywordHits[theme] = hits.slice(0, 120);
    }
    const samples = {
      sender: info.name,
      totalMessages: msgs.length,
      first50: msgs.slice(0, 50),
      last50: msgs.slice(-50),
      quarterly,
      longMessages: msgs.filter(m => m.content.length > 100).slice(0, 200),
      behaviorPatterns: behaviorPatterns.patternsBySender[info.name] || {},
      principleStatements: (principleStatements.statementsBySender[info.name] || []).slice(0, 120),
      structuralTensions: (structuralTensions.contradictionsBySender[info.name] || []).slice(0, 20),
      keywordHits
    };
    writeJson(path.join(samplesDir, `${safeName(info.name)}_samples.json`), samples);

    validation[info.name] = {};
    for (const [theme, hits] of Object.entries(keywordHits)) {
      const uniqueMonths = [...new Set(hits.map(h => h.month))];
      validation[info.name][theme] = {
        status: uniqueMonths.length >= 3 ? "High" : uniqueMonths.length >= 2 ? "Medium" : "Low",
        uniqueMonths: uniqueMonths.length,
        evidence: hits.slice(0, 8)
      };
    }
  }
  writeJson(path.join(analysisDir, "cross_validation.json"), validation);

  const evidenceLedger = {
    version: 1,
    status: "scaffold",
    note: "Populate during interpretation. Analyzer only prepares source-backed samples.",
    claims: [],
    evidenceSources: {
      structure: path.join(analysisDir, "structure.json"),
      participantMap: path.join(analysisDir, "participant_map.json"),
      stats: path.join(analysisDir, "stats.json"),
      samplesDir,
      behaviorPatterns: path.join(analysisDir, "behavior_patterns.json"),
      principleStatements: path.join(analysisDir, "principle_statements.json"),
      structuralTensions: path.join(analysisDir, "contradictions.json"),
      cognitiveBreakWindows: path.join(analysisDir, "cognitive_break_windows.json"),
      coreThreadBurn: path.join(analysisDir, "core_thread_burn.md"),
      crossValidation: path.join(analysisDir, "cross_validation.json")
    }
  };
  writeJson(path.join(evidenceDir, "evidence_ledger.json"), evidenceLedger);

  const findings = {
    version: 1,
    status: "scaffold",
    route: args.route || "orientation",
    findings: [],
    confidenceSummary: {
      high: 0,
      medium: 0,
      low: 0,
      insufficient: 0
    }
  };
  writeJson(path.join(findingsDir, "findings.json"), findings);

  fs.writeFileSync(
    path.join(analysisDir, "core_thread_burn.md"),
    [
      "# Core Thread Burn",
      "",
      "This file must be populated before deep profile reports, generated personal skills, or sensitive identity/persona interpretation.",
      "",
      "## Raw Quote Pile",
      "",
      "Add 15-20 mixed direct quotes here. Do not classify, rank, or sort them by topic.",
      "",
      "## One Problem Hypothesis",
      "",
      "If these quotes are all from the same person, what recurring problem are they trying to solve?",
      "",
      "## Contradiction Test",
      "",
      "Open `_analysis/contradictions.json` for the target person. Start with the highest-ranked structural tension candidate.",
      "",
      "Priority: Type 6 long_denial_to_admission > Type 1 principle_vs_behavior > Type 5 stance_reversal. Within the same type, use High > Medium > Low.",
      "",
      "The hypothesis must explain both poles without flattening either pole. Flattening means dismissing one side as unimportant, temporary, fake, or not real.",
      "",
      "If the hypothesis cannot explain a High-confidence tension after three attempts, either burn again or downgrade to Weak Thread / No Stable Thread. Do not force one grand explanation.",
      "",
      "## Mandatory Verification",
      "",
      "For each proposed core claim:",
      "",
      "1. List 3 dated quotes that directly support it.",
      "2. Name concrete evidence that would falsify it.",
      "3. List quotes that contradict or complicate it.",
      "4. Name at least one alternative explanation.",
      "",
      "If verification is weak, mark the claim as Hypothesis and do not build the report on it.",
      "",
      "## Core Thread",
      "",
      "Only write this if verification succeeds. Compress the working thread into 1-2 sentences. Treat it as a hypothesis, not final truth.",
      "",
      "## Evidence That Does Not Fit",
      "",
      "List strong evidence that resists the thread. Revise or downgrade if necessary.",
      "",
      "## Burn Result",
      "",
      "Choose one: Core Thread Found / Weak Thread / No Stable Thread.",
      ""
    ].join("\n"),
    "utf8"
  );

  fs.writeFileSync(
    path.join(reviewDir, "preview.md"),
    [
      "# Review Preview",
      "",
      "This file is populated after interpretation, before finalizing sensitive claims or generated personal skills.",
      "",
      "## Confirm Before Finalizing",
      "",
      "- High-confidence claims",
      "- Medium/low-confidence claims",
      "- Missing data or alias uncertainty",
      "- Third-party privacy boundary",
      ""
    ].join("\n"),
    "utf8"
  );

  const summary = {
    runtimeStatus: "SmokeTested",
    outputDir: baseOut,
    totalMessages: normalized.length,
    senderCount: senderList.length,
    humanParticipantCount: participantMap.humanParticipants.length,
    nonHumanBucketCount: participantMap.nonHumanBuckets.length,
    topSenders: senderList.slice(0, 10),
    files: {
      manifest: path.join(baseOut, "_manifest.json"),
      normalizedMessages: path.join(normalizedDir, "messages.json"),
      structure: path.join(analysisDir, "structure.json"),
      participantMap: path.join(analysisDir, "participant_map.json"),
      stats: path.join(analysisDir, "stats.json"),
      senderList: path.join(profilesDir, "_sender_list.json"),
      behaviorPatterns: path.join(analysisDir, "behavior_patterns.json"),
      principleStatements: path.join(analysisDir, "principle_statements.json"),
      structuralTensions: path.join(analysisDir, "contradictions.json"),
      cognitiveBreakWindows: path.join(analysisDir, "cognitive_break_windows.json"),
      coreThreadBurn: path.join(analysisDir, "core_thread_burn.md"),
      crossValidation: path.join(analysisDir, "cross_validation.json"),
      evidenceLedger: path.join(evidenceDir, "evidence_ledger.json"),
      findings: path.join(findingsDir, "findings.json"),
      reviewPreview: path.join(reviewDir, "preview.md")
    }
  };
  writeJson(path.join(analysisDir, "run_summary.json"), summary);
  console.log(JSON.stringify(summary, null, 2));
}

try {
  main();
} catch (error) {
  console.error(error.stack || String(error));
  process.exit(1);
}
