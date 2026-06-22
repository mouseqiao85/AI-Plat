import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, Card, Empty, Input, List, message, Popconfirm, Select, Spin, Tag, Upload } from "antd";
import type { UploadProps } from "antd";
import {
  BarChartOutlined,
  BranchesOutlined,
  DeleteOutlined,
  ExportOutlined,
  LinkOutlined,
  NodeIndexOutlined,
  ReloadOutlined,
  SearchOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { knowledgeGraphApi } from "../services/api";
import type {
  KnowledgeGraphStats,
  KnowledgeImportJob,
  KnowledgeImportResult,
  KnowledgeNeighbors,
  KnowledgeNode,
  KnowledgeSource,
  KnowledgeSubgraph,
} from "../types";

const emptyStats: KnowledgeGraphStats = {
  sources: 0,
  nodes: 0,
  edges: 0,
  notes: 0,
  tags: 0,
  entities: 0,
  folders: 0,
  last_import_at: null,
};

const nodeTypeLabel: Record<string, string> = {
  note: "笔记",
  tag: "标签",
  entity: "实体",
  folder: "文件夹",
};

const edgeTypeLabel: Record<string, string> = {
  links_to: "链接到",
  has_tag: "标记为",
  mentions: "提及",
  aliases: "别名",
};

type GraphPoint = { x: number; y: number };

function formatDate(value?: string | null) {
  if (!value) return "暂无";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function edgeLabel(type: string) {
  return edgeTypeLabel[type] || type;
}

function nodeColor(nodeType: string) {
  if (nodeType === "note") return "blue";
  if (nodeType === "tag") return "green";
  if (nodeType === "entity") return "purple";
  if (nodeType === "folder") return "gold";
  return "default";
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function buildGraphLayout(graph: KnowledgeSubgraph | null, selectedNodeId: number | null): Map<number, GraphPoint> {
  const positions = new Map<number, GraphPoint>();
  const graphNodes = graph?.nodes || [];
  if (!graphNodes.length) return positions;

  const selectedIndex = selectedNodeId ? graphNodes.findIndex((node) => node.id === selectedNodeId) : -1;
  const center = selectedIndex >= 0 ? graphNodes[selectedIndex] : graphNodes[0];
  const ringNodes = graphNodes.filter((node) => node.id !== center.id);
  positions.set(center.id, { x: 50, y: 50 });

  ringNodes.forEach((node, index) => {
    const angle = ((Math.PI * 2) / Math.max(ringNodes.length, 1)) * index - Math.PI / 2;
    const radius = ringNodes.length > 32 ? 43 : ringNodes.length > 14 ? 39 : 33;
    const stagger = ringNodes.length > 18 && index % 2 === 1 ? -7 : 0;
    positions.set(node.id, {
      x: clamp(50 + Math.cos(angle) * (radius + stagger), 7, 93),
      y: clamp(50 + Math.sin(angle) * (radius + stagger) * 0.82, 8, 92),
    });
  });

  return positions;
}

function propertiesPreview(node: KnowledgeNode | null) {
  if (!node?.properties || Object.keys(node.properties).length === 0) return "{}";
  return JSON.stringify(node.properties, null, 2);
}

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function NodeCard({ node, active, onClick }: { node: KnowledgeNode; active?: boolean; onClick: () => void }) {
  return (
    <button className={`kg-node-card${active ? " active" : ""}`} onClick={onClick} type="button">
      <div className="kg-node-card-top">
        <strong>{node.title}</strong>
        <Tag color={nodeColor(node.node_type)}>{nodeTypeLabel[node.node_type] || node.node_type}</Tag>
      </div>
      <div className="kg-node-key">{node.path || node.key}</div>
      {node.content_preview && <p>{node.content_preview}</p>}
    </button>
  );
}

export default function KnowledgeGraphPage() {
  const [stats, setStats] = useState<KnowledgeGraphStats>(emptyStats);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [jobs, setJobs] = useState<KnowledgeImportJob[]>([]);
  const [nodes, setNodes] = useState<KnowledgeNode[]>([]);
  const [neighbors, setNeighbors] = useState<KnowledgeNeighbors | null>(null);
  const [subgraph, setSubgraph] = useState<KnowledgeSubgraph | null>(null);
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [nodeType, setNodeType] = useState<string>("");
  const [selectedSourceId, setSelectedSourceId] = useState<string>("");
  const [graphDepth, setGraphDepth] = useState<1 | 2>(1);
  const [sourceName, setSourceName] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [lastImport, setLastImport] = useState<KnowledgeImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [importing, setImporting] = useState(false);
  const [deletingSourceId, setDeletingSourceId] = useState<number | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);

  const activeSourceId = selectedSourceId ? Number(selectedSourceId) : undefined;
  const activeSource = activeSourceId ? sources.find((source) => source.id === activeSourceId) : null;

  const statCards = useMemo(() => [
    { label: "知识源", value: stats.sources, hint: `最近导入：${formatDate(stats.last_import_at)}` },
    { label: "笔记节点", value: stats.notes, hint: "来自 Obsidian Markdown" },
    { label: "标签/实体", value: stats.tags + stats.entities, hint: `${stats.tags} 标签 / ${stats.entities} 实体 / ${stats.folders || 0} 文件夹` },
    { label: "关系边", value: stats.edges, hint: "links_to / has_tag / mentions" },
  ], [stats]);

  const graphNodes = subgraph?.nodes || [];
  const graphEdges = subgraph?.edges || [];
  const graphLayout = useMemo(() => buildGraphLayout(subgraph, selectedNodeId), [subgraph, selectedNodeId]);
  const relationRows = neighbors?.edges || [];
  const detailProperties = useMemo(() => propertiesPreview(selectedNode), [selectedNode]);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, sourceRes, jobsRes, nodeRes, graphRes] = await Promise.all([
        knowledgeGraphApi.getStats(),
        knowledgeGraphApi.listSources(),
        knowledgeGraphApi.listImportJobs(5),
        knowledgeGraphApi.searchNodes({ source_id: activeSourceId, limit: 12 }),
        knowledgeGraphApi.getSubgraph({ source_id: activeSourceId, limit: 80 }),
      ]);
      setStats(statsRes);
      setSources(sourceRes);
      setJobs(jobsRes);
      setNodes(nodeRes);
      setSubgraph(graphRes);
      setNeighbors(null);
      setSelectedNode(null);
      setSelectedNodeId(null);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "知识图谱加载失败");
    } finally {
      setLoading(false);
    }
  }, [activeSourceId]);

  useEffect(() => { loadOverview(); }, [loadOverview]);

  const loadNodeContext = async (node: KnowledgeNode, depth = graphDepth) => {
    setGraphLoading(true);
    try {
      const [neighborRes, graphRes] = await Promise.all([
        knowledgeGraphApi.getNeighbors(node.id, { depth, direction: "both", limit: 160 }),
        knowledgeGraphApi.getSubgraph({ node_id: node.id, depth, limit: 160 }),
      ]);
      setNeighbors(neighborRes);
      setSubgraph(graphRes);
    } catch (err) {
      setNeighbors(null);
      message.error(err instanceof Error ? err.message : "邻居关系加载失败");
    } finally {
      setGraphLoading(false);
    }
  };

  const runSearch = async () => {
    setSearching(true);
    setNeighbors(null);
    setSelectedNode(null);
    setSelectedNodeId(null);
    try {
      const searchQuery = query.trim();
      const [nodeRes, graphRes] = await Promise.all([
        knowledgeGraphApi.searchNodes({
          q: searchQuery,
          node_type: nodeType,
          source_id: activeSourceId,
          limit: 50,
        }),
        knowledgeGraphApi.getSubgraph({
          q: searchQuery,
          source_id: activeSourceId,
          limit: 100,
        }),
      ]);
      setNodes(nodeRes);
      setSubgraph(graphRes);
      if (!nodeRes.length) message.info("未找到匹配节点");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "节点搜索失败");
    } finally {
      setSearching(false);
    }
  };

  const selectNode = async (node: KnowledgeNode) => {
    setSelectedNode(node);
    setSelectedNodeId(node.id);
    await loadNodeContext(node);
  };

  const refreshGraph = async () => {
    setGraphLoading(true);
    try {
      if (selectedNode) {
        await loadNodeContext(selectedNode);
        return;
      }
      const graphRes = await knowledgeGraphApi.getSubgraph({
        q: query.trim(),
        source_id: activeSourceId,
        limit: 120,
      });
      setSubgraph(graphRes);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "图谱刷新失败");
    } finally {
      setGraphLoading(false);
    }
  };

  const exportGraph = () => {
    if (!subgraph || subgraph.nodes.length === 0) {
      message.warning("暂无可导出的子图");
      return;
    }
    downloadJson(`knowledge-subgraph-${Date.now()}.json`, {
      exported_at: new Date().toISOString(),
      query: query.trim(),
      source: activeSource || null,
      selected_node: selectedNode || null,
      subgraph,
    });
  };

  const openNodeUri = () => {
    if (!selectedNode?.uri) return;
    window.open(selectedNode.uri, "_blank", "noopener,noreferrer");
  };

  const uploadProps: UploadProps = {
    accept: ".zip",
    maxCount: 1,
    beforeUpload: (file) => {
      setImportFile(file);
      return false;
    },
    onRemove: () => {
      setImportFile(null);
    },
  };

  const handleImport = async () => {
    if (!importFile) {
      message.warning("请先选择 Obsidian vault zip 文件");
      return;
    }
    setImporting(true);
    try {
      const res = await knowledgeGraphApi.importObsidianVault(importFile, sourceName.trim() || undefined);
      setLastImport(res);
      message.success(`导入完成：${res.stats.notes} 篇笔记，${res.stats.relations} 条关系`);
      setImportFile(null);
      await loadOverview();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Obsidian 导入失败");
    } finally {
      setImporting(false);
    }
  };

  const deleteSource = async (source: KnowledgeSource) => {
    setDeletingSourceId(source.id);
    try {
      const res = await knowledgeGraphApi.deleteSource(source.id);
      message.success(`已删除 ${source.name}：${res.nodes} 个节点，${res.edges} 条关系`);
      if (selectedSourceId === String(source.id)) {
        setSelectedSourceId("");
      }
      setSelectedNode(null);
      setSelectedNodeId(null);
      setNeighbors(null);
      await loadOverview();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "知识源删除失败");
    } finally {
      setDeletingSourceId(null);
    }
  };

  return (
    <div className="kg-page">
      <div className="kg-hero">
        <div>
          <div className="kg-eyebrow">Knowledge Graph Workspace</div>
          <h1>知识图谱管理与可视化</h1>
          <p>
            围绕 Obsidian 知识库形成可管理的图谱工作台：导入、过滤、搜索、查看邻居、检查节点详情并导出当前子图。
          </p>
          <div className="kg-hero-tags">
            <Tag color="blue">Obsidian Vault</Tag>
            <Tag color="purple">Property Graph</Tag>
            <Tag color="green">子图可视化</Tag>
          </div>
        </div>
        <div className="kg-hero-card">
          <BarChartOutlined className="kg-hero-icon" />
          <div className="kg-hero-card-title">运行状态</div>
          <div className="kg-progress-number">功能已上线</div>
          <div className="kg-hero-card-desc">已接入图谱 API、知识源过滤、节点详情、关系图谱和 JSON 导出。</div>
        </div>
      </div>

      <Spin spinning={loading}>
        <div className="kg-stat-grid">
          {statCards.map((item) => (
            <div className="kg-stat-card" key={item.label}>
              <div className="kg-stat-value">{item.value}</div>
              <div className="kg-stat-label">{item.label}</div>
              <div className="kg-stat-hint">{item.hint}</div>
            </div>
          ))}
        </div>
      </Spin>

      <div className="kg-workbench-grid">
        <Card className="kg-import-panel" bordered={false}>
          <div className="kg-panel-title">
            <UploadOutlined /> 导入 Obsidian 知识库
          </div>
          <p className="kg-panel-desc">上传 vault zip，解析 Markdown、frontmatter tags、正文标签和 wikilinks。</p>
          <Input
            placeholder="知识库名称（可选，默认使用 zip 文件名）"
            value={sourceName}
            onChange={(e) => setSourceName(e.target.value)}
          />
          <Upload {...uploadProps} fileList={importFile ? [{ uid: "obsidian", name: importFile.name, status: "done" }] : []}>
            <Button icon={<UploadOutlined />} style={{ marginTop: 12 }}>选择 vault.zip</Button>
          </Upload>
          <Button type="primary" block loading={importing} onClick={handleImport} style={{ marginTop: 12 }}>
            开始导入
          </Button>
          {lastImport && (
            <div className="kg-import-summary">
              <Tag color="blue">笔记 {lastImport.stats.notes}</Tag>
              <Tag color="green">标签 {lastImport.stats.tags}</Tag>
              <Tag color="purple">实体 {lastImport.stats.entities}</Tag>
              <Tag color="gold">文件夹 {lastImport.stats.folders || 0}</Tag>
              <Tag color="orange">关系 {lastImport.stats.relations}</Tag>
              <Tag>跳过 {lastImport.stats.skipped}</Tag>
            </div>
          )}

          <div className="kg-source-list">
            <div className="kg-source-title">知识源</div>
            {sources.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无知识源" />
            ) : (
              sources.slice(0, 6).map((source) => (
                <div
                  key={source.id}
                  className={`kg-source-row${selectedSourceId === String(source.id) ? " active" : ""}`}
                >
                  <button
                    className="kg-source-select"
                    type="button"
                    onClick={() => setSelectedSourceId(selectedSourceId === String(source.id) ? "" : String(source.id))}
                  >
                    <span>{source.name}</span>
                    <small>{formatDate(source.created_at)}</small>
                  </button>
                  <Popconfirm
                    title="删除知识源"
                    description="会同时删除该知识源的节点、关系和导入记录。"
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => deleteSource(source)}
                  >
                    <Button
                      aria-label={`删除知识源 ${source.name}`}
                      className="kg-source-delete"
                      danger
                      icon={<DeleteOutlined />}
                      loading={deletingSourceId === source.id}
                      size="small"
                      type="text"
                    />
                  </Popconfirm>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="kg-search-panel" bordered={false}>
          <div className="kg-panel-title">
            <SearchOutlined /> 查询与过滤
          </div>
          <div className="kg-search-controls">
            <Input
              placeholder="搜索笔记、标签或实体..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onPressEnter={runSearch}
              allowClear
            />
            <Select
              value={selectedSourceId}
              onChange={setSelectedSourceId}
              options={[
                { value: "", label: "全部知识源" },
                ...sources.map((source) => ({ value: String(source.id), label: source.name })),
              ]}
              style={{ minWidth: 150 }}
            />
            <Select
              value={nodeType}
              onChange={setNodeType}
              options={[
                { value: "", label: "全部节点" },
                { value: "note", label: "笔记" },
                { value: "tag", label: "标签" },
                { value: "entity", label: "实体" },
                { value: "folder", label: "文件夹" },
              ]}
              style={{ minWidth: 120 }}
            />
            <Button type="primary" icon={<SearchOutlined />} loading={searching} onClick={runSearch}>搜索</Button>
            <Button icon={<ReloadOutlined />} onClick={loadOverview}>刷新</Button>
          </div>
          <div className="kg-filter-summary">
            <Tag color={activeSource ? "processing" : "default"}>{activeSource?.name || "全部知识源"}</Tag>
            <Tag color={nodeType ? "blue" : "default"}>{nodeType ? nodeTypeLabel[nodeType] : "全部类型"}</Tag>
            <Tag>{nodes.length} 个列表节点</Tag>
            <Tag>{graphNodes.length} 个子图节点</Tag>
          </div>
        </Card>
      </div>

      <div className="kg-visual-grid">
        <Card
          className="kg-result-panel kg-graph-panel"
          bordered={false}
          title={<span><NodeIndexOutlined /> 关系图谱</span>}
          extra={(
            <div className="kg-graph-actions">
              <Select
                size="small"
                value={graphDepth}
                onChange={(value) => {
                  setGraphDepth(value);
                  if (selectedNode) void loadNodeContext(selectedNode, value);
                }}
                options={[
                  { value: 1, label: "1 跳" },
                  { value: 2, label: "2 跳" },
                ]}
                style={{ width: 82 }}
              />
              <Button size="small" icon={<ReloadOutlined />} loading={graphLoading} onClick={refreshGraph} />
              <Button size="small" icon={<ExportOutlined />} onClick={exportGraph}>导出</Button>
            </div>
          )}
        >
          <Spin spinning={graphLoading}>
            {graphNodes.length === 0 ? (
              <Empty description="暂无可视化数据" />
            ) : (
              <div className="kg-graph-canvas">
                <svg className="kg-graph-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {graphEdges.map((edge) => {
                    const from = graphLayout.get(edge.from_node_id);
                    const to = graphLayout.get(edge.to_node_id);
                    if (!from || !to) return null;
                    return (
                      <line
                        key={edge.id}
                        x1={from.x}
                        y1={from.y}
                        x2={to.x}
                        y2={to.y}
                        className={`kg-graph-edge ${edge.edge_type}`}
                      />
                    );
                  })}
                </svg>
                {graphNodes.map((node) => {
                  const point = graphLayout.get(node.id) || { x: 50, y: 50 };
                  return (
                    <button
                      key={node.id}
                      type="button"
                      className={`kg-graph-node ${node.node_type}${selectedNodeId === node.id ? " active" : ""}`}
                      style={{ left: `${point.x}%`, top: `${point.y}%` }}
                      onClick={() => selectNode(node)}
                      title={node.title}
                    >
                      <span>{node.title}</span>
                      <small>{nodeTypeLabel[node.node_type] || node.node_type}</small>
                    </button>
                  );
                })}
              </div>
            )}
          </Spin>
        </Card>

        <Card className="kg-result-panel" bordered={false} title="节点详情">
          {!selectedNode ? (
            <Empty description="选择一个节点查看详情" />
          ) : (
            <div className="kg-detail-panel">
              <div className="kg-detail-title">
                <div>
                  <h3>{selectedNode.title}</h3>
                  <Tag color={nodeColor(selectedNode.node_type)}>{nodeTypeLabel[selectedNode.node_type] || selectedNode.node_type}</Tag>
                </div>
                <Button size="small" icon={<LinkOutlined />} disabled={!selectedNode.uri} onClick={openNodeUri}>
                  Obsidian
                </Button>
              </div>
              <div className="kg-detail-grid">
                <span>Key</span><strong>{selectedNode.key}</strong>
                <span>路径</span><strong>{selectedNode.path || "-"}</strong>
                <span>Source ID</span><strong>{selectedNode.source_id}</strong>
                <span>更新时间</span><strong>{formatDate(selectedNode.updated_at)}</strong>
                <span>邻居关系</span><strong>{relationRows.length}</strong>
              </div>
              {selectedNode.content_preview && <p className="kg-detail-preview">{selectedNode.content_preview}</p>}
              <pre className="kg-property-box">{detailProperties}</pre>
            </div>
          )}
        </Card>
      </div>

      <div className="kg-result-grid">
        <Card className="kg-result-panel" bordered={false} title="节点列表">
          {nodes.length === 0 ? (
            <Empty description="暂无节点。请先导入 Obsidian vault 或调整搜索条件。" />
          ) : (
            <div className="kg-node-list">
              {nodes.map((node) => (
                <NodeCard key={node.id} node={node} active={selectedNodeId === node.id} onClick={() => selectNode(node)} />
              ))}
            </div>
          )}
        </Card>

        <Card className="kg-result-panel" bordered={false} title={<span><BranchesOutlined /> 邻居关系</span>}>
          {!neighbors ? (
            <Empty description="点击节点查看一跳或二跳邻居关系" />
          ) : (
            <>
              <div className="kg-neighbor-center">
                <strong>{neighbors.center.title}</strong>
                <Tag>{nodeTypeLabel[neighbors.center.node_type] || neighbors.center.node_type}</Tag>
              </div>
              <List
                size="small"
                dataSource={neighbors.edges}
                locale={{ emptyText: "暂无关系" }}
                renderItem={(edge) => {
                  const from = edge.from_node_id === neighbors.center.id
                    ? neighbors.center
                    : neighbors.nodes.find((node) => node.id === edge.from_node_id);
                  const to = edge.to_node_id === neighbors.center.id
                    ? neighbors.center
                    : neighbors.nodes.find((node) => node.id === edge.to_node_id);
                  return (
                    <List.Item className="kg-relation-row">
                      <span>{from?.title || edge.from_node_id}</span>
                      <Tag color="blue">{edgeLabel(edge.edge_type)}</Tag>
                      <span>{to?.title || edge.to_node_id}</span>
                    </List.Item>
                  );
                }}
              />
            </>
          )}
        </Card>
      </div>

      <Card className="kg-result-panel" bordered={false} title="最近导入">
        {jobs.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无导入记录" />
        ) : (
          <List
            size="small"
            dataSource={jobs}
            renderItem={(job) => (
              <List.Item>
                <span>{job.filename}</span>
                <span className="kg-job-meta">
                  <Tag color={job.status === "completed" ? "success" : job.status === "failed" ? "error" : "processing"}>{job.status}</Tag>
                  {formatDate(job.completed_at || job.created_at)}
                </span>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
