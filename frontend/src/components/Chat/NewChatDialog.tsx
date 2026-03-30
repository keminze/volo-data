"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import "@ant-design/v5-patch-for-react-19";
import { message } from "antd";
import { createChat } from "@/lib/api/chat";
import { useChatStore } from "@/store/chatStore";
import { useRouter } from "next/navigation";
import { useDataSourceStore } from "@/store/dataSourceStore";
import { useExampleDataSourceStore } from "@/store/dataSourceStore";
import { getOrCreateUUID } from "@/lib/utils";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NewChatDialog({ open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const router = useRouter();
  const { refreshChats } = useChatStore();
  const { dataSources, fetchDataSources } = useDataSourceStore();
  const { exampleDataSources, fetchExampleDataSources } = useExampleDataSourceStore();

  useEffect(() => {
    if (open) {
      fetchDataSources();
      fetchExampleDataSources();
    }
  }, [open, fetchDataSources,fetchExampleDataSources]);

  const [form, setForm] = useState({
    name: "",
    description: "",
    connection_id: "",
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      return message.warning(t("chat.enterChatName"));
    }
    if (!form.connection_id) {
      return message.warning(t("chat.selectDataSource"));
    }

    try {
      setLoading(true);

      const res = await createChat({
        name: form.name,
        description: form.description,
        user_id: getOrCreateUUID(),
        connection_id: Number(form.connection_id),
      });

      const newChat = {
        id: res?.conversation_id,
        name: form.name,
        connection_id: Number(form.connection_id),
      };

      refreshChats();

      message.success(t("chat.createSuccess"));
      onOpenChange(false);
      router.push(`/chat/${newChat.id}?connection_id=${newChat.connection_id}`);
    } catch (err) {
      console.error("创建聊天失败:", err);
      message.error(t("chat.createError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("chat.newChat")}</DialogTitle>
          <DialogDescription>{t("chat.selectDataSourceAndCreate")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* 聊天名称 */}
          <div>
            <label className="text-sm text-gray-600">{t("chat.chatName")}</label>
            <Input
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder={t("chat.enterChatName")}
            />
          </div>

          {/* 数据源选择 */}
          <div>
            <label className="text-sm text-gray-600">{t("chat.selectDataSource")}</label>
            <Select onValueChange={(v) => handleChange("connection_id", v)} value={form.connection_id}>
              <SelectTrigger>
                <SelectValue placeholder={t("chat.selectDataSource")} />
              </SelectTrigger>
              <SelectContent>
                {dataSources.length === 0 && exampleDataSources.length === 0 ? (
                  <div className="p-2 text-gray-400 text-sm">{t("chat.noDataSource")}</div>
                ) : (
                  <>
                    {exampleDataSources.map((eds) => (
                      <SelectItem key={`example-${eds.id}`} value={`example-${eds.id}`}>
                        🌟 {t("chat.example")}: {eds.name} ({eds.db_type})
                      </SelectItem>
                    ))}

                    {dataSources.map((ds) => (
                      <SelectItem key={`ds-${ds.id}`} value={String(ds.id)}>
                        {ds.name} ({ds.db_type})
                      </SelectItem>
                    ))}
                  </>
                )}
              </SelectContent>
            </Select>
          </div>

          {/* 聊天描述 */}
          <div>
            <label className="text-sm text-gray-600">{t("chat.description")}</label>
            <Textarea
              value={form.description}
              onChange={(e) => handleChange("description", e.target.value)}
              placeholder={t("chat.enterDescription")}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? t("common.loading") : t("chat.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

