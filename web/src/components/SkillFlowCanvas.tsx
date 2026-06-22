import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import dagre from "dagre";
import { Button, Empty, Input, Select, Tag, Tooltip } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import "@xyflow/react/dist/style.css";
import type { DagFlowEdge, DagFlowNode } from "../types";

const NODE_WIDTH = 190;
const NODE_HEIGHT = 70;

export interface SkillCanvasRole {
  id: string;
  name: string;
  description?: string;
  category?: string;
}

interface CanvasNodeData extends Record<string, unknown> {
  label: string;
  subtitle: string;
  kind: "role" | "graphrag";
}

interface SkillFlowCanvasProps {
  roleIds: string[];
  extraNodes: DagFlowNode[];
  edges: DagFlowEdge[];
  rolesById: Map<string, SkillCanvasRole>;
  onEdgesChange: (edges: DagFlowEdge[]) => void;
  onExtraNodesChange: (nodes: DagFlowNode[]) => void;
  height?: number | string;
}

const roleNodeId = (roleId: string, index: number) => {
  const safe = roleId.replace(/[^A-Za-z0-9_-]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  return safe || `node-${index + 1}`;
};

const graphRagRoleId = (nodeId: string) => `graphrag:${nodeId}`;

const buildNodes = (
  roleIds: string[],
  extraNodes: DagFlowNode[],
  rolesById: Map<string, SkillCanvasRole>,
): Node<CanvasNodeData>[] => {
  const baseNodes: Node<CanvasNodeData>[] = roleIds.map((roleId, index) => {
    const role = rolesById.get(roleId);
    return {
      id: roleNodeId(roleId, index),
      type: "default",
      position: { x: index * 230, y: 40 },
      data: {
        label: role?.name || roleId,
        subtitle: role?.category || roleId,
        kind: "role",
      },
      style: {
        width: NODE_WIDTH,
        minHeight: NODE_HEIGHT,
        borderRadius: 8,
        border: "1px solid #91caff",
        background: "#f0f7ff",
        color: "#1f1f1f",
        fontSize: 12,
      },
    };
  });

  const knowledgeNodes: Node<CanvasNodeData>[] = extraNodes.map((node, index) => ({
    id: node.id,
    type: "default",
    position: { x: index * 230, y: 180 },
    data: {
      label: node.label || "GraphRAG",
      subtitle: `${Number(node.max_hits || 3)} hits`,
      kind: "graphrag",
    },
    style: {
      width: NODE_WIDTH,
      minHeight: NODE_HEIGHT,
      borderRadius: 8,
      border: "1px solid #ffd666",
      background: "#fffbe6",
      color: "#1f1f1f",
      fontSize: 12,
    },
  }));

  return layoutNodes([...knowledgeNodes, ...baseNodes], []);
};

const layoutNodes = (nodes: Node<CanvasNodeData>[], edges: Edge[]): Node<CanvasNodeData>[] => {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 44, ranksep: 72, marginx: 20, marginy: 20 });
  nodes.forEach((node) => graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);
  return nodes.map((node) => {
    const pos = graph.node(node.id);
    if (!pos) return node;
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });
};

const toReactFlowEdges = (edges: DagFlowEdge[], nodeIds: Set<string>): Edge[] =>
  edges
    .filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to) && edge.from !== edge.to)
    .map((edge) => ({
      id: `${edge.from}->${edge.to}`,
      source: edge.from,
      target: edge.to,
      animated: true,
      style: { stroke: "#597ef7", strokeWidth: 1.6 },
    }));

const fromReactFlowEdges = (edges: Edge[]): DagFlowEdge[] => {
  const seen = new Set<string>();
  const next: DagFlowEdge[] = [];
  for (const edge of edges) {
    if (!edge.source || !edge.target || edge.source === edge.target) continue;
    const key = `${edge.source}->${edge.target}`;
    if (seen.has(key)) continue;
    seen.add(key);
    next.push({ from: edge.source, to: edge.target });
  }
  return next;
};

export default function SkillFlowCanvas({
  roleIds,
  extraNodes,
  edges,
  rolesById,
  onEdgesChange,
  onExtraNodesChange,
  height = 360,
}: SkillFlowCanvasProps) {
  const [nodes, setNodes] = useState<Node<CanvasNodeData>[]>([]);
  const [flowEdges, setFlowEdges] = useState<Edge[]>([]);

  const canonicalNodes = useMemo(() => buildNodes(roleIds, extraNodes, rolesById), [roleIds, extraNodes, rolesById]);
  const nodeIds = useMemo(() => new Set(canonicalNodes.map((node) => node.id)), [canonicalNodes]);

  useEffect(() => {
    const rfEdges = toReactFlowEdges(edges, nodeIds);
    setNodes(layoutNodes(canonicalNodes, rfEdges));
    setFlowEdges(rfEdges);
  }, [canonicalNodes, edges, nodeIds]);

  const handleNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((current) => applyNodeChanges(changes, current) as Node<CanvasNodeData>[]);
  }, []);

  const handleEdgesChange = useCallback((changes: EdgeChange[]) => {
    setFlowEdges((current) => {
      const next = applyEdgeChanges(changes, current);
      onEdgesChange(fromReactFlowEdges(next));
      return next;
    });
  }, [onEdgesChange]);

  const handleConnect = useCallback((connection: Connection) => {
    if (!connection.source || !connection.target || connection.source === connection.target) return;
    setFlowEdges((current) => {
      const next = addEdge({
        ...connection,
        id: `${connection.source}->${connection.target}`,
        animated: true,
        style: { stroke: "#597ef7", strokeWidth: 1.6 },
      }, current);
      onEdgesChange(fromReactFlowEdges(next));
      return next;
    });
  }, [onEdgesChange]);

  const addGraphRagNode = () => {
    const existingIds = new Set([...roleIds.map(roleNodeId), ...extraNodes.map((node) => node.id)]);
    let index = 1;
    let id = "graphrag";
    while (existingIds.has(id)) {
      index += 1;
      id = `graphrag-${index}`;
    }
    onExtraNodesChange([
      ...extraNodes,
      { id, type: "graphrag", role_id: graphRagRoleId(id), label: "GraphRAG", query_template: "{input}", max_hits: 3 },
    ]);
  };

  const updateGraphRagNode = (id: string, patch: Partial<DagFlowNode>) => {
    onExtraNodesChange(extraNodes.map((node) => (node.id === id ? { ...node, ...patch } : node)));
  };

  const removeGraphRagNode = (id: string) => {
    onExtraNodesChange(extraNodes.filter((node) => node.id !== id));
    onEdgesChange(edges.filter((edge) => edge.from !== id && edge.to !== id));
  };

  const removeEdge = (edgeId: string) => {
    const next = flowEdges.filter((edge) => edge.id !== edgeId);
    setFlowEdges(next);
    onEdgesChange(fromReactFlowEdges(next));
  };

  return (
    <div style={{
      height,
      minHeight: 0,
      border: "1px solid #e8e8e8",
      borderRadius: 8,
      overflow: "hidden",
      background: "#fff",
      display: "flex",
      flexDirection: "column",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderBottom: "1px solid #f0f0f0", flexShrink: 0 }}>
        <Tag color="gold" style={{ margin: 0 }}>DAG</Tag>
        <span style={{ fontSize: 12, color: "#8c8c8c", flex: 1 }}>
          拖动画布节点，连接节点端点定义执行依赖。
        </span>
        <Button size="small" icon={<PlusOutlined />} onClick={addGraphRagNode}>
          GraphRAG
        </Button>
      </div>

      <div style={{ flex: 1, minHeight: 0, background: "#fbfbfb" }}>
        {nodes.length === 0 ? (
          <Empty description="从右侧角色树选择节点" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ paddingTop: 140 }} />
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={flowEdges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={handleConnect}
            fitView
            fitViewOptions={{ padding: 0.22 }}
            nodesDraggable
            nodesConnectable
            elementsSelectable
          >
            <MiniMap pannable zoomable nodeColor={(node) => node.data?.kind === "graphrag" ? "#ffd666" : "#91caff"} />
            <Controls />
            <Background gap={18} size={1} color="#e6e6e6" />
          </ReactFlow>
        )}
      </div>

      <div style={{ display: "grid", gap: 8, padding: 10, borderTop: "1px solid #f0f0f0", flexShrink: 0, maxHeight: 168, overflow: "auto" }}>
        {extraNodes.length > 0 && (
          <div style={{ display: "grid", gap: 6 }}>
            {extraNodes.map((node) => (
              <div key={node.id} style={{ display: "grid", gridTemplateColumns: "92px minmax(0, 1fr) 90px auto", gap: 6, alignItems: "center" }}>
                <Tag color="gold" style={{ margin: 0 }}>{node.id}</Tag>
                <Input
                  size="small"
                  value={node.query_template || "{input}"}
                  onChange={(event) => updateGraphRagNode(node.id, { query_template: event.target.value })}
                  placeholder="GraphRAG 查询模板"
                />
                <Select
                  size="small"
                  value={Number(node.max_hits || 3)}
                  onChange={(value) => updateGraphRagNode(node.id, { max_hits: value })}
                  options={[1, 2, 3, 5, 8, 10].map((value) => ({ value, label: `${value} hits` }))}
                />
                <Tooltip title="删除 GraphRAG 节点">
                  <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeGraphRagNode(node.id)} />
                </Tooltip>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {flowEdges.length === 0 ? (
            <span style={{ color: "#bfbfbf", fontSize: 12 }}>暂无依赖，节点将并行执行。</span>
          ) : flowEdges.map((edge) => {
            const source = nodes.find((node) => node.id === edge.source);
            const target = nodes.find((node) => node.id === edge.target);
            return (
              <Tag key={edge.id} closable onClose={() => removeEdge(edge.id)} style={{ margin: 0 }}>
                {source?.data.label || edge.source}{" -> "}{target?.data.label || edge.target}
              </Tag>
            );
          })}
        </div>
      </div>
    </div>
  );
}
