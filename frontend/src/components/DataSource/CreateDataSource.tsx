"use client"

import { useState, useRef } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Upload, File as FileIcon, X } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { createConnection, getTables } from "@/lib/api/connections"
import { useDataSourceStore } from "@/store/dataSourceStore"
import { message } from "antd"
import { getOrCreateUUID } from "@/lib/utils"

export function NewDataSourceDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
}) {
  const { fetchDataSources } = useDataSourceStore()
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState<1 | 2>(1)
  const [tables, setTables] = useState<{ table_name: string; comment: string }[]>([]);
  const [dbType, setDbType] = useState<string>("")
  const fileRef = useRef<HTMLInputElement | null>(null)
  const [page, setPage] = useState(1);
  const [searchKeyword, setSearchKeyword] = useState("");

  // 根据关键词筛选
  const filteredTables = tables.filter(
    (t) =>
      t.table_name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
      (t.comment && t.comment.toLowerCase().includes(searchKeyword.toLowerCase()))
  );

  const [form, setForm] = useState<any>({
    user_id: getOrCreateUUID(),
    name: "未命名数据源",
    db_description: "",
    db_type: "",
    db_url: "",
    db_file: null,
    user: "",
    password: "",
    host: "",
    port: "",
    dbname: "",
    train_tables: [] as string[],
  })

  /** 更新表单字段 */
  const handleChange = (key: string, value: any) => {
    setForm((prev: any) => ({ ...prev, [key]: value }))
  }

  /** 上传文件 */
  const handleFileChange = (files: FileList | null) => {
    const file = files && files[0] ? files[0] : null
    setForm((prev: any) => ({ ...prev, db_file: file }))
  }

  /** 移除文件 */
  const removeFile = () => {
    setForm((prev: any) => ({ ...prev, db_file: null }))
    if (fileRef.current) fileRef.current.value = ""
  }

  /** 下一步：连接数据库，获取表列表 */
  const handleNextStep = async () => {
    setLoading(true)
    try {
      const formData = new FormData()
      for (const key in form) {
        if (form[key] !== null && form[key] !== "") {
          formData.append(key, form[key])
        }
      }
      formData.append("db_type", dbType)

      const res = await getTables(formData)
      const data: Record<string, string>[] = res.tables;

      const formatted = data.map(item => ({
        table_name: item.table_name,
        comment: item.comment || "",
      }));

      setTables(formatted);
      setStep(2)
      message.success("成功获取数据表")
    } catch (err) {
      console.error("❌ 获取表失败:", err)
      message.error("获取数据表失败，请检查连接信息")
    } finally {
      setLoading(false)
    }
  }

  /** 创建数据源 */
  const handleCreate = async () => {
    setLoading(true)
    try {
      const formData = new FormData()
      for (const key in form) {
        if (form[key] !== null && form[key] !== "") {
          // ✅ train_tables 特殊处理
          if (key === "train_tables") {
            form.train_tables.forEach((table: string) => {
              formData.append("train_tables", table)
            })
          } else {
            formData.append(key, form[key])
          }
        }
      }
      // formData.append("db_type", dbType)
      // formData.append("train_tables", JSON.stringify(form.train_tables))

      const res = await createConnection(formData)
      message.success("数据源创建成功")
      fetchDataSources()
      resetForm()
      onOpenChange(false)
    } catch (err) {
      console.error("❌ 创建数据源失败:", err)
      message.error("创建失败，请稍后重试")
    } finally {
      setLoading(false)
    }
  }

  /** 重置表单 */
  const resetForm = () => {
    setDbType("")
    setForm({
      user_id: getOrCreateUUID(),
      name: "未命名数据源",
      db_description: "",
      db_type: "",
      db_url: "",
      db_file: null,
      user: "",
      password: "",
      host: "",
      port: "",
      dbname: "",
      train_tables: [] as string[],
    })
    setStep(1)
    if (fileRef.current) fileRef.current.value = ""
  }

  /** 关闭弹窗 */
  const handleDialogChange = (v: boolean) => {
    if (!v) resetForm()
    onOpenChange(v)
  }

  /** 切换数据库类型 */
  const handleTypeChange = (v: string) => {
    setDbType(v)
    setForm({
      ...form,
      db_type: v,
      db_file: null,
      db_url: "",
      user: "",
      password: "",
      host: "",
      port: "",
      dbname: "",
      train_tables: [],
    })
  }

  /** 渲染表单字段 */
  const renderFields = () => {
    switch (dbType) {
      case "sqlite":
        return (
          <>
            <Label>数据库 URL（或选择文件）</Label>
            <Input
              placeholder="https://example.com/db.sqlite"
              value={form.db_url}
              onChange={(e) => handleChange("db_url", e.target.value)}
              disabled={!!form.db_file}
            />
            <Label>或上传 SQLite 文件</Label>
            <div className="flex items-center gap-2">
              <input
                ref={fileRef}
                type="file"
                accept=".sqlite,.db,.sqlite3"
                className="hidden"
                onChange={(e) => handleFileChange(e.target.files)}
              />
              {!form.db_file ? (
                <Button variant="outline" onClick={() => fileRef.current?.click()}>
                  <Upload className="w-4 h-4 mr-2" />
                  选择文件
                </Button>
              ) : (
                <div className="flex items-center justify-between w-full border rounded-lg px-3 py-2 bg-gray-50">
                  <div className="flex items-center text-sm text-gray-700 truncate max-w-[180px]">
                    <FileIcon className="w-4 h-4 mr-2 text-primary" />
                    {form.db_file.name}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={removeFile}
                    className="text-gray-500 hover:text-red-500"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          </>
        )

      case "mysql":
      case "postgres":
        return (
          <>
            <Label>主机地址</Label>
            <Input
              placeholder="localhost"
              value={form.host}
              onChange={(e) => handleChange("host", e.target.value)}
            />
            <Label>端口</Label>
            <Input
              type="number"
              placeholder={dbType === "mysql" ? "3306" : "5432"}
              value={form.port}
              onChange={(e) => handleChange("port", e.target.value)}
            />
            <Label>用户名</Label>
            <Input
              placeholder="username"
              value={form.user}
              onChange={(e) => handleChange("user", e.target.value)}
            />
            <Label>密码</Label>
            <Input
              type="password"
              placeholder="password"
              value={form.password}
              onChange={(e) => handleChange("password", e.target.value)}
            />
            <Label>数据库名称</Label>
            <Input
              placeholder="database"
              value={form.dbname}
              onChange={(e) => handleChange("dbname", e.target.value)}
            />
          </>
        )

      case "excel":
        return (
          <>
            <Label>上传 Excel 文件</Label>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files)}
            />
            {!form.db_file ? (
              <Button variant="outline" onClick={() => fileRef.current?.click()}>
                <Upload className="w-4 h-4 mr-2" />
                选择文件
              </Button>
            ) : (
              <div className="flex items-center justify-between w-full border rounded-lg px-3 py-2 bg-gray-50">
                <div className="flex items-center text-sm text-gray-700 truncate max-w-[180px]">
                  <FileIcon className="w-4 h-4 mr-2 text-primary" />
                  {form.db_file.name}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={removeFile}
                  className="text-gray-500 hover:text-red-500"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            )}
          </>
        )

      case "csv":
        return (
          <>
            <Label>上传 CSV 文件</Label>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files)}
            />
            {!form.db_file ? (
              <Button variant="outline" onClick={() => fileRef.current?.click()}>
                <Upload className="w-4 h-4 mr-2" />
                选择文件
              </Button>
            ) : (
              <div className="flex items-center justify-between w-full border rounded-lg px-3 py-2 bg-gray-50">
                <div className="flex items-center text-sm text-gray-700 truncate max-w-[180px]">
                  <FileIcon className="w-4 h-4 mr-2 text-primary" />
                  {form.db_file.name}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={removeFile}
                  className="text-gray-500 hover:text-red-500"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            )}
          </>
        )

      default:
        return <p className="text-gray-500 text-sm">请选择数据源类型以继续</p>
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleDialogChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>新建数据源</DialogTitle>
          <DialogDescription>
            {step === 1
              ? "填写数据源基础信息并选择类型。"
              : "请选择要用于训练的数据表（可多选）。"}
          </DialogDescription>
        </DialogHeader>

        {/* 第一步 */}
        {step === 1 && (
          <div className="space-y-4 py-2">
            <Label>数据源名称</Label>
            <Input
              placeholder="如：公司销售数据库"
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
            />
            <Label>附加说明</Label>
            <Textarea
              placeholder="可填写该数据源的用途或简介"
              value={form.db_description}
              onChange={(e) => handleChange("db_description", e.target.value)}
            />
            <Label>数据源类型</Label>
            <Select value={dbType} onValueChange={handleTypeChange}>
              <SelectTrigger>
                <SelectValue placeholder="请选择数据源类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sqlite">SQLite</SelectItem>
                <SelectItem value="mysql">MySQL</SelectItem>
                <SelectItem value="postgres">PostgreSQL</SelectItem>
                <SelectItem value="excel">Excel</SelectItem>
                <SelectItem value="csv">CSV</SelectItem>
              </SelectContent>
            </Select>
            <div className="space-y-3">{renderFields()}</div>
          </div>
        )}

        {/* 第二步 */}
        {step === 2 && (
          <div className="space-y-4 py-2">
            <Label>选择要用于训练的数据表（最多可选 20 个）</Label>

            {/* ✅ 操作栏：关键词搜索 + 一键选择按钮 */}
            <div className="flex items-center justify-between mb-2 space-x-2">
              <input
                type="text"
                placeholder="输入关键词筛选表名或注释..."
                className="flex-1 border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={searchKeyword}
                onChange={(e) => {
                  setSearchKeyword(e.target.value);
                  setPage(1); // 输入新关键词后重置页码
                }}
              />

              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setForm((prev: any) => {
                    if (prev.train_tables.length > 0) {
                      // 如果已有选择，则清空
                      return { ...prev, train_tables: [] };
                    } else {
                      // 一键选中前20个（筛选后）
                      const selected = filteredTables.slice(0, 20);
                      return { ...prev, train_tables: selected };
                    }
                  });
                }}
              >
                {form.train_tables.length > 0 ? "清空选择" : "一键选择前 20 个"}
              </Button>

              <span className="text-sm text-gray-500 whitespace-nowrap">
                已选择 {form.train_tables.length} / 20
              </span>
            </div>

            {/* ✅ 分页 + 筛选显示区域 */}
            <div className="border rounded-lg p-3 max-h-80 overflow-y-auto">
              {filteredTables.length > 0 ? (
                <>
                  {filteredTables
                    .slice((page - 1) * 10, page * 10)
                    .map((table, idx) => (
                      <div
                        key={`${table.table_name ?? "table"}-${idx}`}
                        className="flex items-center justify-between space-x-2 border-b py-2"
                      >
                        <label className="flex items-center space-x-2 cursor-pointer flex-1">
                          <input
                            type="checkbox"
                            checked={form.train_tables.includes(table.table_name)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                // 最多只能选择 20 个
                                if (form.train_tables.length >= 20) {
                                  message.warning("最多只能选择 20 个数据表");
                                  return;
                                }

                                // 添加表名
                                setForm((prev: any) => {
                                  const exists = prev.train_tables.includes(table.table_name);
                                  return exists
                                    ? prev
                                    : {
                                        ...prev,
                                        train_tables: [...prev.train_tables, table.table_name],
                                      };
                                });
                              } else {
                                // 移除表名
                                setForm((prev: any) => ({
                                  ...prev,
                                  train_tables: prev.train_tables.filter(
                                    (t: string) => t !== table.table_name
                                  ),
                                }));
                              }
                            }}
                          />
                          <div className="flex flex-col truncate">
                            <span className="text-sm font-medium truncate">
                              {table.table_name}
                            </span>
                            <span className="text-xs text-gray-500 truncate">
                              {table.comment || "无注释"}
                            </span>
                          </div>
                        </label>
                      </div>
                    ))}

                  {/* ✅ 分页控制 */}
                  <div className="flex justify-between items-center mt-3 text-sm">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(p - 1, 1))}
                      disabled={page === 1}
                    >
                      上一页
                    </Button>
                    <span>
                      第 {page} / {Math.ceil(filteredTables.length / 10)} 页
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setPage((p) =>
                          Math.min(p + 1, Math.ceil(filteredTables.length / 10))
                        )
                      }
                      disabled={page === Math.ceil(filteredTables.length / 10)}
                    >
                      下一页
                    </Button>
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-500">
                  未找到符合条件的数据表，请更换关键词。
                </p>
              )}
            </div>
          </div>
        )}

        {/* 按钮区 */}
        <DialogFooter>
          {step === 1 ? (
            <>
              <Button
                variant="outline"
                onClick={() => handleDialogChange(false)}
                disabled={loading}
              >
                取消
              </Button>
              <Button
                onClick={async () => {
                  if (dbType === "excel" || dbType === "csv") {
                    // ✅ Excel/CSV 直接创建
                    await handleCreate();
                  } else {
                    // ✅ 其他类型继续下一步（进入表选择）
                    handleNextStep();
                  }
                }}
                disabled={!dbType || loading}
              >
                {loading
                  ? "处理中..."
                  : dbType === "excel" || dbType === "csv"
                  ? "创建"
                  : "下一步"}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                disabled={loading}
              >
                上一步
              </Button>
              <Button
                variant="outline"
                onClick={() => handleDialogChange(false)}
                disabled={loading}
              >
                取消
              </Button>
              <Button
                onClick={handleCreate}
                disabled={loading || form.train_tables.length === 0}
              >
                {loading ? "创建中..." : "创建"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
