import { useState } from "react";
import { Modal, Input, Button, Steps, message, Alert, Tag, Spin } from "antd";
import { GithubOutlined, ImportOutlined, CheckCircleFilled } from "@ant-design/icons";
import { tabsApi } from "../services/api";
import type { TabRole, TabScenario } from "../types";

interface ImportSkillModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ImportSkillModal({ open, onClose, onSuccess }: ImportSkillModalProps) {
  const [step, setStep] = useState(0);
  const [tabName, setTabName] = useState("");
  const [tabId, setTabId] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [importing, setImporting] = useState(false);
  const [importedRoles, setImportedRoles] = useState<TabRole[]>([]);
  const [importedScenarios, setImportedScenarios] = useState<TabScenario[]>([]);
  const [error, setError] = useState("");

  const reset = () => {
    setStep(0);
    setTabName("");
    setTabId("");
    setGithubUrl("");
    setBranch("main");
    setImporting(false);
    setImportedRoles([]);
    setImportedScenarios([]);
    setError("");
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const generateId = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9一-龥]+/g, "-")
      .replace(/^-|-$/g, "") || "custom-tab";
  };

  const handleNameChange = (val: string) => {
    setTabName(val);
    setTabId(generateId(val));
  };

  const validateUrl = (url: string): boolean => {
    return /^https?:\/\/github\.com\/[^/]+\/[^/]+/.test(url.trim());
  };

  const handleImport = async () => {
    if (!tabName.trim()) {
      message.warning("请输入 Tab 名称");
      return;
    }
    if (!githubUrl.trim() || !validateUrl(githubUrl)) {
      message.warning("请输入有效的 GitHub 仓库链接");
      return;
    }

    setImporting(true);
    setError("");
    setStep(1);

    try {
      // Step 1: Create tab
      await tabsApi.createTab({
        id: tabId,
        name: tabName.trim(),
        source_type: "github",
        source_url: githubUrl.trim(),
        branch,
      });

      setStep(2);

      // Step 2: Import
      const result = await tabsApi.importTab(tabId, {
        url: githubUrl.trim(),
        branch,
      });

      if (result.success) {
        setImportedRoles(result.roles || []);
        setImportedScenarios(result.scenarios || []);
        setStep(3);
        message.success(`导入成功：${result.imported} 个角色，${result.scenarios_generated} 个场景`);
      } else {
        setError("导入失败");
        setStep(0);
      }
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "导入失败";
      setError(errMsg);
      setStep(0);
      // Cleanup: try to delete the tab if it was created
      try { await tabsApi.deleteTab(tabId); } catch { /* ignore */ }
    } finally {
      setImporting(false);
    }
  };

  const handleDone = () => {
    onSuccess();
    handleClose();
  };

  return (
    <Modal
      title={
        <span>
          <GithubOutlined style={{ marginRight: 8 }} />
          从 GitHub 导入 Skill
        </span>
      }
      open={open}
      onCancel={handleClose}
      footer={null}
      width={640}
      destroyOnClose
    >
      <Steps
        current={step}
        size="small"
        style={{ marginBottom: 24 }}
        items={[
          { title: "配置" },
          { title: "克隆" },
          { title: "分析分类" },
          { title: "完成" },
        ]}
      />

      {error && (
        <Alert type="error" message={error} showIcon closable
          onClose={() => setError("")} style={{ marginBottom: 16 }} />
      )}

      {step === 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontWeight: 500 }}>
              Tab 名称
            </label>
            <Input
              placeholder="例如：金融"
              value={tabName}
              onChange={(e) => handleNameChange(e.target.value)}
            />
            {tabId && (
              <span style={{ fontSize: 12, color: "#888", marginTop: 4, display: "block" }}>
                ID: {tabId}
              </span>
            )}
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 4, fontWeight: 500 }}>
              GitHub 仓库链接
            </label>
            <Input
              placeholder="https://github.com/anthropics/financial-services"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              prefix={<GithubOutlined />}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 4, fontWeight: 500 }}>
              分支 (可选)
            </label>
            <Input
              placeholder="main"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
            />
          </div>

          <Button
            type="primary"
            icon={<ImportOutlined />}
            onClick={handleImport}
            disabled={!tabName.trim() || !githubUrl.trim()}
            block
          >
            一键导入
          </Button>
        </div>
      )}

      {(step === 1 || step === 2) && importing && (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <Spin size="large" />
          <p style={{ marginTop: 16, color: "#666" }}>
            {step === 1 ? "正在克隆仓库..." : "正在 LLM 分析分类..."}
          </p>
        </div>
      )}

      {step === 3 && (
        <div>
          <Alert
            type="success"
            message={`导入完成：${importedRoles.length} 个角色`}
            showIcon
            icon={<CheckCircleFilled />}
            style={{ marginBottom: 16 }}
          />

          <div style={{ marginBottom: 16 }}>
            <h4 style={{ marginBottom: 8 }}>导入的角色：</h4>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {importedRoles.map((r) => (
                <Tag
                  key={r.id}
                  color={r.classification === "planning" ? "blue" : "green"}
                >
                  {r.display_name || r.role_id}
                  <span style={{ fontSize: 10, marginLeft: 4 }}>
                    ({r.classification === "planning" ? "规划" : "实现"})
                  </span>
                </Tag>
              ))}
            </div>
          </div>

          {importedScenarios.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ marginBottom: 8 }}>生成的场景：</h4>
              {importedScenarios.map((s) => (
                <div key={s.id} style={{ padding: "4px 0" }}>
                  <Tag color="purple">{s.name}</Tag>
                  <span style={{ fontSize: 12, color: "#666" }}>{s.description}</span>
                </div>
              ))}
            </div>
          )}

          <Button type="primary" onClick={handleDone} block>
            完成
          </Button>
        </div>
      )}
    </Modal>
  );
}
