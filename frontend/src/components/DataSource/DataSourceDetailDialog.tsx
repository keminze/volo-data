"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { message } from "antd";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dataSource: {
    id: number | string;
    name: string;
    db_type: string;
    db_description?: string;
  };
  onSave?: (updated: { name: string; db_description: string }) => Promise<void> | void;
}

export function DataSourceDetailDialog({ open, onOpenChange, dataSource, onSave }: Props) {
  const [form, setForm] = useState({
    name: dataSource.name || "",
    db_description: dataSource.db_description || "",
  });
  const [saving, setSaving] = useState(false);

  const handleChange = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      if (onSave) {
        await onSave(form);
        message.success("保存成功");
      }
      else {
        message.warning("示例数据源不可修改");
      }
      onOpenChange(false);
    } catch (err) {
      console.error("保存失败:", err);
      message.error("保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>数据源详情</DialogTitle>
          <DialogDescription>查看和编辑数据源信息</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div>
            <label className="text-sm text-gray-600">名称</label>
            <Input
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder="请输入数据源名称"
            />
          </div>

          <div>
            <label className="text-sm text-gray-600">类型</label>
            <Input value={dataSource.db_type} disabled className="bg-gray-100" />
          </div>

          <div>
            <label className="text-sm text-gray-600">描述</label>
            <Textarea
              value={form.db_description}
              onChange={(e) => handleChange("db_description", e.target.value)}
              placeholder="请输入数据源描述"
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
