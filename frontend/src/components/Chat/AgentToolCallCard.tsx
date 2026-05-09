"use client";
import { useState } from "react";
import { ChevronRight, Wrench } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { base16AteliersulphurpoolLight } from "react-syntax-highlighter/dist/esm/styles/prism";

interface ToolCallEntry {
  name: string;
  args?: Record<string, any>;
  result?: string;
}

function CollapsibleSection({
  label,
  defaultOpen = false,
  children,
}: {
  label: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-t border-gray-100">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 px-3 py-1.5 w-full text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <ChevronRight
          size={12}
          className={`transition-transform duration-200 ${open ? "rotate-90" : ""}`}
        />
        <span>{label}</span>
      </button>
      {open && <div className="px-3 pb-2">{children}</div>}
    </div>
  );
}

export default function AgentToolCallCard({ toolCalls }: { toolCalls: ToolCallEntry[] }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="w-full max-w-[90%] sm:max-w-[85%] md:max-w-[80%] lg:max-w-[70%] mb-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <ChevronRight
          size={14}
          className={`transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
        />
        <Wrench size={14} />
        <span>{t("chat.toolCallsCount", { count: toolCalls.length })}</span>
      </button>

      {expanded && (
        <div className="ml-4 space-y-2 mt-1">
          {toolCalls.map((tc, idx) => (
            <div
              key={idx}
              className="border border-gray-200 rounded-lg overflow-hidden bg-gray-50"
            >
              {/* 工具名称 */}
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 border-b border-gray-200">
                <Wrench size={12} className="text-gray-500" />
                <span className="text-sm font-medium text-gray-700">{tc.name}</span>
              </div>

              {/* 参数（可折叠） */}
              {tc.args && Object.keys(tc.args).length > 0 && (
                <CollapsibleSection label={t("chat.toolArgs")}>
                  <SyntaxHighlighter
                    language="json"
                    style={base16AteliersulphurpoolLight}
                    customStyle={{
                      margin: 0,
                      padding: "8px",
                      fontSize: "11px",
                      borderRadius: "6px",
                      maxHeight: "150px",
                    }}
                  >
                    {JSON.stringify(tc.args, null, 2)}
                  </SyntaxHighlighter>
                </CollapsibleSection>
              )}

              {/* 结果（可折叠） */}
              {tc.result && (
                <CollapsibleSection label={t("chat.toolResult")}>
                  <pre className="text-xs text-gray-600 bg-white border border-gray-200 rounded p-2 overflow-x-auto max-h-[200px]">
                    {tc.result}
                  </pre>
                </CollapsibleSection>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
