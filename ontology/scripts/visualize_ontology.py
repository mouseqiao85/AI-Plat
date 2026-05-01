#!/usr/bin/env python3
"""
本体知识图谱可视化脚本 v3 — 纯 JS/SVG 自包含，零外部依赖
生成包含三个视图的自包含交互式 HTML（无 CDN，离线可用）：
  1. 概念节点 & 规则关系图谱（SVG 力导向图，可拖拽）
  2. 规则类型分布（饼图 + 柱状图）
  3. 条款来源分布（横向条形图）

用法：
  python3 visualize_ontology.py --kb /path/to/ontology_kb.json --output /path/to/out.html
"""

import json
import argparse
import sys
import math
import random
from collections import Counter
from pathlib import Path


def load_kb(kb_path: str) -> dict:
    p = Path(kb_path)
    if not p.exists():
        print(f"[ERROR] 本体文件不存在: {kb_path}", file=sys.stderr)
        print("[HINT] 请先执行 ingest 模式导入制度文件。", file=sys.stderr)
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def build_all_node_ids(kb: dict) -> dict:
    id_map = {}
    for cname in kb.get("concepts", {}).keys():
        id_map[cname] = cname
    gov = kb.get("concepts", {}).get("GovernanceStructure", {})
    for role_key in gov.get("roles", {}).keys():
        id_map[role_key] = role_key
    for rule in kb.get("rules", []):
        rid = rule.get("rule_id", "")
        if rid:
            id_map[rid] = rid
    for rule in kb.get("rules", []):
        for target in rule.get("applies_to", []):
            if target not in id_map:
                id_map[target] = target
    return id_map


def build_graph_data(kb: dict, id_map: dict) -> tuple:
    nodes = []
    links = []
    node_ids_added = set()

    RULE_COLORS = {
        "veto":      "#dc2626",
        "condition": "#2563eb",
        "threshold": "#16a34a",
        "exception": "#d97706",
    }
    CONCEPT_COLOR = "#7c3aed"
    ROLE_COLOR    = "#059669"
    ENTITY_COLOR  = "#6b7280"

    def add_node(nid, name, size, color, category, tooltip):
        if nid not in node_ids_added:
            short = name[:16] + "…" if len(name) > 16 else name
            nodes.append({
                "id":       nid,
                "name":     short,
                "fullName": name,
                "size":     size,
                "color":    color,
                "category": category,
                "tooltip":  tooltip,
            })
            node_ids_added.add(nid)

    # 顶层概念节点
    for cname, cdata in kb.get("concepts", {}).items():
        desc = cdata.get("definition", cname) if isinstance(cdata, dict) else cname
        add_node(cname, cname, 36, CONCEPT_COLOR, "concept",
                 f"概念: {cname}\\n{desc[:60]}")

    # 治理架构角色节点
    gov = kb.get("concepts", {}).get("GovernanceStructure", {})
    for role_key, role_data in gov.get("roles", {}).items():
        role_name = role_data.get("name", role_key) if isinstance(role_data, dict) else role_key
        add_node(role_key, role_name, 26, ROLE_COLOR, "role",
                 f"治理角色: {role_name}")
        links.append({
            "source": role_key,
            "target": "GovernanceStructure",
            "type":   "belongs",
            "label":  "属于",
        })

    # 规则节点
    for rule in kb.get("rules", []):
        rid   = rule.get("rule_id", "")
        rtype = rule.get("rule_type", "condition")
        color = RULE_COLORS.get(rtype, ENTITY_COLOR)
        clause = rule.get("source_clause", "")
        desc   = rule.get("description", "")[:60]
        add_node(rid, f"{rid} {clause}", 20, color, "rule",
                 f"{rid} [{rtype}]\\n{clause}\\n{desc}")
        for target in rule.get("applies_to", []):
            tid = id_map.get(target, target)
            if tid not in node_ids_added:
                add_node(tid, target, 22, ENTITY_COLOR, "entity",
                         f"实体: {target}")
            links.append({
                "source": rid,
                "target": tid,
                "type":   "applies",
                "label":  "适用",
            })

    # 显式关系边
    for rel in kb.get("relations", []):
        src = id_map.get(rel.get("from", ""), rel.get("from", ""))
        tgt = id_map.get(rel.get("to",   ""), rel.get("to",   ""))
        rtype = rel.get("type", "")
        for nid, nname in [(src, rel.get("from", "")), (tgt, rel.get("to", ""))]:
            if nid not in node_ids_added:
                add_node(nid, nname, 22, ENTITY_COLOR, "entity",
                         f"实体: {nname}")
        links.append({
            "source": src,
            "target": tgt,
            "type":   "relation",
            "label":  rtype,
        })

    return nodes, links


def build_rule_charts(kb: dict):
    TYPE_ZH = {
        "veto":      "一票否决",
        "condition": "条件规则",
        "threshold": "阈值规则",
        "exception": "例外条款",
    }
    TYPE_COLORS = {
        "veto":      "#dc2626",
        "condition": "#2563eb",
        "threshold": "#16a34a",
        "exception": "#d97706",
    }
    counter = Counter(r.get("rule_type", "unknown") for r in kb.get("rules", []))
    pie_data = [
        {"name": TYPE_ZH.get(k, k), "value": v, "color": TYPE_COLORS.get(k, "#9ca3af")}
        for k, v in counter.items()
    ]
    src_counter = Counter(r.get("source_doc", "未知") for r in kb.get("rules", []))
    src_data = [
        {"name": (k[:28] + "…" if len(k) > 28 else k), "value": v}
        for k, v in src_counter.items()
    ]
    return pie_data, src_data


def assign_initial_positions(nodes: list, cx: float = 500, cy: float = 300,
                              radius: float = 200) -> list:
    rng = random.Random(42)
    n = len(nodes)
    # 按 category 分层：concept 在内圈，role 中圈，rule 外圈，entity 最外
    order = {"concept": 0, "role": 1, "rule": 2, "entity": 3}
    sorted_nodes = sorted(nodes, key=lambda nd: order.get(nd["category"], 4))
    for i, node in enumerate(sorted_nodes):
        angle = (i / n) * 2 * math.pi
        r = radius + rng.uniform(-40, 40)
        node["x"] = round(cx + r * math.cos(angle), 2)
        node["y"] = round(cy + r * math.sin(angle), 2)
    return sorted_nodes


# ---------------------------------------------------------------------------
# HTML template — uses __PLACEHOLDER__ substitution (avoids f-string escaping)
# ---------------------------------------------------------------------------
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>本体知识图谱 — __DOCNO__</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#f1f5f9;color:#1e293b}
header{background:linear-gradient(135deg,#1e1b4b,#3730a3);color:#fff;padding:16px 24px}
header h1{font-size:18px;font-weight:700;margin-bottom:4px}
.meta{font-size:12px;opacity:.85;line-height:1.8}
.badges{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.badge{background:rgba(255,255,255,.18);border-radius:20px;padding:2px 12px;font-size:12px}
.tabs{display:flex;background:#fff;border-bottom:2px solid #e2e8f0;padding:0 24px;
  box-shadow:0 1px 4px rgba(0,0,0,.06)}
.tab{padding:12px 20px;cursor:pointer;font-size:14px;border-bottom:3px solid transparent;
  color:#64748b;transition:all .2s;user-select:none}
.tab.active,.tab:hover{color:#3730a3;border-bottom-color:#3730a3;font-weight:600}
.panel{display:none;padding:20px 24px}
.panel.active{display:block}
.card{background:#fff;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.07);
  padding:16px;margin-bottom:16px}
.card-title{font-size:13px;font-weight:600;color:#374151;margin-bottom:12px;
  padding-left:10px;border-left:4px solid #3730a3}
.row{display:flex;gap:16px}
.row .card{flex:1;min-width:0}
.stat-row{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.stat{background:#fff;border-radius:8px;padding:10px 18px;flex:1;min-width:110px;
  box-shadow:0 2px 6px rgba(0,0,0,.06);text-align:center}
.stat-val{font-size:24px;font-weight:700;color:#3730a3}
.stat-label{font-size:11px;color:#64748b;margin-top:2px}
.legend{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px;font-size:12px}
.ld{display:flex;align-items:center;gap:5px}
.ldot{width:11px;height:11px;border-radius:50%;flex-shrink:0}
.tip{font-size:11px;color:#94a3b8;margin-top:8px}
#graph-svg{width:100%;height:580px;border-radius:8px;background:#fafbff;cursor:default}
#tooltip{position:fixed;background:rgba(15,23,42,.88);color:#f8fafc;padding:7px 12px;
  border-radius:7px;font-size:12px;max-width:260px;line-height:1.6;
  pointer-events:none;display:none;z-index:9999;white-space:pre-wrap}
</style>
</head>
<body>
<div id="tooltip"></div>
<header>
  <h1>本体知识图谱可视化</h1>
  <div class="meta">
    来源：__SOURCE_DOCS__<br/>
    发文机关：__ISSUER__ &nbsp;|&nbsp; 文号：__DOCNO__ &nbsp;|&nbsp; 发布日期：__DATE__<br/>
    知识库更新：__UPDATED__
  </div>
  <div class="badges">
    <span class="badge">概念节点 __CONCEPT_COUNT__ 个</span>
    <span class="badge">规则条目 __RULE_COUNT__ 条</span>
    <span class="badge">图谱节点 __NODE_COUNT__ 个</span>
    <span class="badge">关系边 __LINK_COUNT__ 条</span>
  </div>
</header>

<div class="tabs">
  <div class="tab active" onclick="switchTab(0)">概念节点 &amp; 规则关系图谱</div>
  <div class="tab" onclick="switchTab(1)">规则分布分析</div>
  <div class="tab" onclick="switchTab(2)">条款来源分布</div>
</div>

<!-- ===== 图谱面板 ===== -->
<div class="panel active" id="p0">
  <div class="stat-row">
    <div class="stat"><div class="stat-val">__CONCEPT_COUNT__</div><div class="stat-label">顶层概念</div></div>
    <div class="stat"><div class="stat-val">__ROLE_COUNT__</div><div class="stat-label">治理角色</div></div>
    <div class="stat"><div class="stat-val">__RULE_COUNT__</div><div class="stat-label">规则节点</div></div>
    <div class="stat"><div class="stat-val">__LINK_COUNT__</div><div class="stat-label">关系边</div></div>
  </div>
  <div class="card">
    <div class="card-title">概念节点 &amp; 规则关系图谱</div>
    <div class="legend">
      <div class="ld"><div class="ldot" style="background:#7c3aed"></div>顶层概念</div>
      <div class="ld"><div class="ldot" style="background:#059669"></div>治理角色</div>
      <div class="ld"><div class="ldot" style="background:#dc2626"></div>一票否决规则</div>
      <div class="ld"><div class="ldot" style="background:#2563eb"></div>条件规则</div>
      <div class="ld"><div class="ldot" style="background:#16a34a"></div>阈值规则</div>
      <div class="ld"><div class="ldot" style="background:#d97706"></div>例外条款</div>
      <div class="ld"><div class="ldot" style="background:#6b7280"></div>其他实体</div>
    </div>
    <svg id="graph-svg" xmlns="http://www.w3.org/2000/svg"></svg>
    <p class="tip">提示：可拖拽节点调整布局 | 滚轮缩放 | 悬停节点查看详情 | 橙色虚线为显式关系边</p>
  </div>
</div>

<!-- ===== 规则分布面板 ===== -->
<div class="panel" id="p1">
  <div class="row">
    <div class="card">
      <div class="card-title">规则类型占比（饼图）</div>
      <svg id="pie-svg" style="width:100%;height:280px"></svg>
    </div>
    <div class="card">
      <div class="card-title">规则类型数量（柱状图）</div>
      <svg id="bar-svg" style="width:100%;height:280px"></svg>
    </div>
  </div>
</div>

<!-- ===== 来源分布面板 ===== -->
<div class="panel" id="p2">
  <div class="card">
    <div class="card-title">各来源文件规则数量</div>
    <svg id="src-svg" style="width:100%;height:200px"></svg>
  </div>
</div>

<script>
// ============================================================
// 数据注入
// ============================================================
const NODES = __NODES__;
const LINKS = __LINKS__;
const PIE_DATA = __PIE_DATA__;
const SRC_DATA = __SRC_DATA__;

// ============================================================
// 标签页切换
// ============================================================
const panels = document.querySelectorAll('.panel');
const tabs   = document.querySelectorAll('.tab');
function switchTab(i) {
  panels.forEach((p,j)=>p.classList.toggle('active',j===i));
  tabs.forEach((t,j)=>t.classList.toggle('active',j===i));
  if (i===1) { drawPie(); drawBar(); }
  if (i===2) { drawSrc(); }
}

// ============================================================
// 力导向图
// ============================================================
(function() {
  const svg = document.getElementById('graph-svg');
  const NS  = 'http://www.w3.org/2000/svg';
  const tip = document.getElementById('tooltip');

  const W = svg.clientWidth  || 900;
  const H = svg.clientHeight || 580;
  let scale = 1, tx = 0, ty = 0;

  // 初始化节点状态
  const nodes = NODES.map(n => ({...n, vx:0, vy:0, fixed:false}));
  const nodeById = {};
  nodes.forEach(n => nodeById[n.id] = n);

  // 解析边（过滤掉找不到端点的边）
  const links = LINKS.map(l => ({
    ...l,
    source: nodeById[l.source],
    target: nodeById[l.target],
  })).filter(l => l.source && l.target);

  // ---- SVG 结构 ----
  // 缩放容器
  const root = document.createElementNS(NS,'g');
  root.setAttribute('id','root-g');
  svg.appendChild(root);

  // 箭头 marker
  const defs = document.createElementNS(NS,'defs');
  defs.innerHTML = `
    <marker id="arr-gray" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
      <path d="M0,0 L0,6 L8,3 z" fill="#cbd5e1"/>
    </marker>
    <marker id="arr-orange" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
      <path d="M0,0 L0,6 L8,3 z" fill="#f97316"/>
    </marker>`;
  svg.insertBefore(defs, root);

  const linkG = document.createElementNS(NS,'g'); root.appendChild(linkG);
  const nodeG = document.createElementNS(NS,'g'); root.appendChild(nodeG);

  // ---- 创建连线元素 ----
  const linkEls = links.map(l => {
    const isRel = l.type === 'relation';
    const line = document.createElementNS(NS,'line');
    line.setAttribute('stroke',        isRel ? '#f97316' : '#cbd5e1');
    line.setAttribute('stroke-width',  isRel ? '2' : '1');
    if (isRel) line.setAttribute('stroke-dasharray','6,3');
    line.setAttribute('marker-end', isRel ? 'url(#arr-orange)' : 'url(#arr-gray)');
    linkG.appendChild(line);

    let labelEl = null;
    if (isRel && l.label) {
      labelEl = document.createElementNS(NS,'text');
      labelEl.setAttribute('font-size','9');
      labelEl.setAttribute('fill','#f97316');
      labelEl.setAttribute('text-anchor','middle');
      labelEl.setAttribute('pointer-events','none');
      labelEl.textContent = l.label;
      linkG.appendChild(labelEl);
    }
    return {line, labelEl, data:l};
  });

  // ---- 创建节点元素 ----
  const nodeEls = nodes.map(n => {
    const g = document.createElementNS(NS,'g');
    g.style.cursor = 'grab';

    const circle = document.createElementNS(NS,'circle');
    circle.setAttribute('r', n.size);
    circle.setAttribute('fill', n.color);
    circle.setAttribute('stroke','#fff');
    circle.setAttribute('stroke-width','2.5');
    circle.setAttribute('opacity','0.92');
    g.appendChild(circle);

    const label = document.createElementNS(NS,'text');
    label.setAttribute('font-size', n.category==='concept' ? '11' : '10');
    label.setAttribute('fill','#1e293b');
    label.setAttribute('text-anchor','middle');
    label.setAttribute('dy', n.size + 12);
    label.setAttribute('pointer-events','none');
    if (n.category==='concept') label.setAttribute('font-weight','700');
    label.textContent = n.name;
    g.appendChild(label);

    // tooltip
    g.addEventListener('mouseenter', e => {
      tip.style.display = 'block';
      tip.textContent   = n.tooltip || n.fullName || n.name;
    });
    g.addEventListener('mousemove', e => {
      tip.style.left = (e.clientX + 14) + 'px';
      tip.style.top  = (e.clientY - 10) + 'px';
    });
    g.addEventListener('mouseleave', () => { tip.style.display='none'; });

    // 拖拽
    let dragging=false, ox=0, oy=0;
    g.addEventListener('mousedown', e => {
      dragging=true; n.fixed=true;
      const pt = svgPoint(e);
      ox = pt.x - n.x; oy = pt.y - n.y;
      g.style.cursor='grabbing';
      e.stopPropagation(); e.preventDefault();
    });
    window.addEventListener('mousemove', e => {
      if (!dragging) return;
      const pt = svgPoint(e);
      n.x = pt.x - ox; n.y = pt.y - oy;
      n.vx=0; n.vy=0;
    });
    window.addEventListener('mouseup', () => {
      if(dragging){dragging=false; n.fixed=false; g.style.cursor='grab';}
    });

    nodeG.appendChild(g);
    return {g, circle, label, data:n};
  });

  // SVG 坐标转换
  function svgPoint(e) {
    const rect = svg.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left - tx) / scale,
      y: (e.clientY - rect.top  - ty) / scale,
    };
  }

  // 滚轮缩放
  svg.addEventListener('wheel', e => {
    e.preventDefault();
    const rect = svg.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const delta = e.deltaY < 0 ? 1.12 : 0.88;
    tx = mx - (mx - tx) * delta;
    ty = my - (my - ty) * delta;
    scale *= delta;
    root.setAttribute('transform',`translate(${tx},${ty}) scale(${scale})`);
  }, {passive:false});

  // ---- 力模拟 ----
  const K=80, REPULSION=4500, GRAVITY=0.015, DAMPING=0.82;
  let frame=0;

  function tick() {
    frame++;

    // 斥力
    for (let i=0;i<nodes.length;i++) {
      for (let j=i+1;j<nodes.length;j++) {
        const a=nodes[i], b=nodes[j];
        const dx=b.x-a.x, dy=b.y-a.y;
        const dist=Math.max(Math.sqrt(dx*dx+dy*dy),1);
        const f=REPULSION/(dist*dist);
        const fx=f*dx/dist, fy=f*dy/dist;
        if(!a.fixed){a.vx-=fx; a.vy-=fy;}
        if(!b.fixed){b.vx+=fx; b.vy+=fy;}
      }
    }

    // 引力（弹簧）
    links.forEach(l=>{
      const a=l.source, b=l.target;
      const dx=b.x-a.x, dy=b.y-a.y;
      const dist=Math.max(Math.sqrt(dx*dx+dy*dy),1);
      const f=(dist-K*2)*0.025;
      const fx=f*dx/dist, fy=f*dy/dist;
      if(!a.fixed){a.vx+=fx; a.vy+=fy;}
      if(!b.fixed){b.vx-=fx; b.vy-=fy;}
    });

    // 重力（收缩到中心）
    nodes.forEach(n=>{
      if(!n.fixed){
        n.vx+=(W/2-n.x)*GRAVITY;
        n.vy+=(H/2-n.y)*GRAVITY;
      }
    });

    // 积分
    nodes.forEach(n=>{
      if(!n.fixed){
        n.vx*=DAMPING; n.vy*=DAMPING;
        n.x+=n.vx; n.y+=n.vy;
      }
    });

    // 更新 DOM
    nodeEls.forEach(ne=>{
      ne.g.setAttribute('transform',`translate(${ne.data.x},${ne.data.y})`);
    });
    linkEls.forEach(le=>{
      const s=le.data.source, t=le.data.target;
      const dx=t.x-s.x, dy=t.y-s.y;
      const dist=Math.sqrt(dx*dx+dy*dy)||1;
      const ex=s.x+dx*(1-t.size/dist);
      const ey=s.y+dy*(1-t.size/dist);
      le.line.setAttribute('x1',s.x); le.line.setAttribute('y1',s.y);
      le.line.setAttribute('x2',ex);  le.line.setAttribute('y2',ey);
      if(le.labelEl){
        le.labelEl.setAttribute('x',(s.x+t.x)/2);
        le.labelEl.setAttribute('y',(s.y+t.y)/2);
      }
    });

    // 运行 6 秒后停止（节省 CPU），之后只在拖拽时刷新
    if(frame < 360) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})();

// ============================================================
// 饼图 (SVG)
// ============================================================
function drawPie() {
  const svg = document.getElementById('pie-svg');
  if (svg.dataset.drawn) return;
  svg.dataset.drawn = '1';
  const W = svg.clientWidth||400, H = svg.clientHeight||280;
  const cx=W*0.42, cy=H*0.48, R=Math.min(cx,cy)*0.7, r=R*0.44;

  const total = PIE_DATA.reduce((s,d)=>s+d.value,0);
  let angle=-Math.PI/2;
  let html='';

  PIE_DATA.forEach((d,i)=>{
    const a0=angle, a1=angle+(d.value/total)*Math.PI*2;
    const x0=cx+R*Math.cos(a0), y0=cy+R*Math.sin(a0);
    const x1=cx+R*Math.cos(a1), y1=cy+R*Math.sin(a1);
    const ix0=cx+r*Math.cos(a0), iy0=cy+r*Math.sin(a0);
    const ix1=cx+r*Math.cos(a1), iy1=cy+r*Math.sin(a1);
    const large=d.value/total>0.5?1:0;
    const pct=Math.round(d.value/total*100);
    const ma=(a0+a1)/2, labelR=R*0.72;
    const lx=cx+labelR*Math.cos(ma), ly=cy+labelR*Math.sin(ma);
    html+=`<path d="M${ix0},${iy0} L${x0},${y0} A${R},${R} 0 ${large},1 ${x1},${y1} L${ix1},${iy1} A${r},${r} 0 ${large},0 ${ix0},${iy0} Z"
      fill="${d.color}" opacity="0.9" stroke="#fff" stroke-width="2"/>`;
    if(pct>=8) html+=`<text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle"
      font-size="11" fill="#fff" font-weight="600">${pct}%</text>`;
    angle=a1;
    // 图例
    const ly2=H*0.1+i*22;
    html+=`<rect x="${W*0.82}" y="${ly2}" width="12" height="12" fill="${d.color}" rx="2"/>
      <text x="${W*0.82+16}" y="${ly2+10}" font-size="11" fill="#374151">${d.name} (${d.value})</text>`;
  });
  svg.innerHTML=html;
}

// ============================================================
// 柱状图 (SVG)
// ============================================================
function drawBar() {
  const svg = document.getElementById('bar-svg');
  if (svg.dataset.drawn) return;
  svg.dataset.drawn = '1';
  const W=svg.clientWidth||400, H=svg.clientHeight||280;
  const PAD={l:40,r:20,t:20,b:50};
  const cw=W-PAD.l-PAD.r, ch=H-PAD.t-PAD.b;
  const maxV=Math.max(...PIE_DATA.map(d=>d.value),1);
  const bw=Math.min(cw/PIE_DATA.length*0.55, 60);
  const gap=cw/PIE_DATA.length;
  let html=`<line x1="${PAD.l}" y1="${PAD.t}" x2="${PAD.l}" y2="${PAD.t+ch}" stroke="#e2e8f0"/>
    <line x1="${PAD.l}" y1="${PAD.t+ch}" x2="${PAD.l+cw}" y2="${PAD.t+ch}" stroke="#e2e8f0"/>`;

  PIE_DATA.forEach((d,i)=>{
    const bh=Math.round((d.value/maxV)*ch*0.9);
    const bx=PAD.l+gap*i+gap/2-bw/2;
    const by=PAD.t+ch-bh;
    html+=`<rect x="${bx}" y="${by}" width="${bw}" height="${bh}" fill="${d.color}" rx="4" opacity="0.9"/>
      <text x="${bx+bw/2}" y="${by-5}" text-anchor="middle" font-size="12" fill="#374151" font-weight="600">${d.value}</text>
      <text x="${bx+bw/2}" y="${PAD.t+ch+16}" text-anchor="middle" font-size="11" fill="#64748b">${d.name}</text>`;
  });
  svg.innerHTML=html;
}

// ============================================================
// 来源横向条形图 (SVG)
// ============================================================
function drawSrc() {
  const svg = document.getElementById('src-svg');
  if (svg.dataset.drawn) return;
  svg.dataset.drawn = '1';
  const W=svg.clientWidth||700, H=svg.clientHeight||200;
  const PAD={l:30,r:60,t:20,b:20};
  const cw=W-PAD.l-PAD.r;
  const rowH=Math.floor((H-PAD.t-PAD.b)/Math.max(SRC_DATA.length,1));
  const bh=Math.min(rowH*0.55, 28);
  const maxV=Math.max(...SRC_DATA.map(d=>d.value),1);
  let html='';
  SRC_DATA.forEach((d,i)=>{
    const bw=Math.round((d.value/maxV)*cw*0.82);
    const by=PAD.t+i*rowH+(rowH-bh)/2;
    html+=`<rect x="${PAD.l}" y="${by}" width="${bw}" height="${bh}" fill="#3730a3" rx="4" opacity="0.85"/>
      <text x="${PAD.l+bw+8}" y="${by+bh/2+4}" font-size="12" fill="#374151" font-weight="600">${d.value} 条</text>
      <text x="${PAD.l-6}" y="${by+bh/2+4}" font-size="11" fill="#64748b" text-anchor="end">${d.name}</text>`;
  });
  svg.innerHTML=html;
}
</script>
</body>
</html>"""


def render_html(kb, nodes, links, pie_data, src_data) -> str:
    j = lambda o: json.dumps(o, ensure_ascii=False)

    concept_count = len(kb.get("concepts", {}))
    rule_count    = len(kb.get("rules", []))
    gov           = kb.get("concepts", {}).get("GovernanceStructure", {})
    role_count    = len(gov.get("roles", {}))
    node_count    = len(nodes)
    link_count    = len(links)

    html = HTML_TEMPLATE
    replacements = {
        "__DOCNO__":         kb.get("doc_number", ""),
        "__SOURCE_DOCS__":   "、".join(kb.get("source_docs", [])),
        "__ISSUER__":        kb.get("issuer", ""),
        "__DATE__":          kb.get("issue_date", ""),
        "__UPDATED__":       kb.get("updated_at", ""),
        "__CONCEPT_COUNT__": str(concept_count),
        "__RULE_COUNT__":    str(rule_count),
        "__ROLE_COUNT__":    str(role_count),
        "__NODE_COUNT__":    str(node_count),
        "__LINK_COUNT__":    str(link_count),
        "__NODES__":         j(nodes),
        "__LINKS__":         j(links),
        "__PIE_DATA__":      j(pie_data),
        "__SRC_DATA__":      j(src_data),
    }
    for k, v in replacements.items():
        html = html.replace(k, v)
    return html


def main():
    parser = argparse.ArgumentParser(description="本体知识图谱可视化生成器 v3（纯 JS/SVG，零外部依赖）")
    parser.add_argument("--kb",     required=True, help="本体 JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出 HTML 文件路径")
    args = parser.parse_args()

    kb = load_kb(args.kb)
    id_map = build_all_node_ids(kb)
    nodes, links = build_graph_data(kb, id_map)
    nodes = assign_initial_positions(nodes)
    pie_data, src_data = build_rule_charts(kb)

    html = render_html(kb, nodes, links, pie_data, src_data)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    print(f"[OK] 可视化文件已生成: {args.output}")
    print(f"     图谱节点: {len(nodes)}  关系边: {len(links)}")
    print(f"     规则总计: {len(kb.get('rules', []))}  顶层概念: {len(kb.get('concepts', {}))}")


if __name__ == "__main__":
    main()
