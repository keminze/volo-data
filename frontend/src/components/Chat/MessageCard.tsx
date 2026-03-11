"use client";
import { useEffect, useRef, useState } from "react";
import ReactECharts from "echarts-for-react";
import "@ant-design/v5-patch-for-react-19";
import { Card, Tabs, Table, Button, message, Tooltip } from "antd";
import {
  FileExcelOutlined,
  CopyOutlined,
  DownloadOutlined,
  LeftOutlined,
  RightOutlined,
} from "@ant-design/icons";
import * as XLSX from "xlsx";
import "./MessageCard.css"; // 👈 我们会在下面写样式

export default function MessageCard({ sql, sample_data, charts, isGeneratingSQL, isGeneratingCharts } : any) {
  const [activeChart, setActiveChart] = useState(0);
  const [isReady, setIsReady] = useState(false);
  const [activeTab, setActiveTab] = useState("table");
  // const [collapsed, setCollapsed] = useState(false);
  const chartRef = useRef<ReactECharts | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const tableData = Array.isArray(sample_data) ? sample_data : [];

  const getRowKey = (record:any) => {
    const base =
      record.id ||
      record.ID ||
      record.key ||
      record.uid ||
      Object.values(record).join("_"); // 拼接一行的全部值
    return `${base}`; // ✅ 确保唯一
  };

  /** 📋 复制 SQL */
  const copySQL = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      message.success("SQL 已复制到剪贴板");
    } catch {
      message.error("复制失败");
    }
  };

  /** 📊 导出图表为 PNG */
  const exportChartAsPng = () => {
    const chartInstance = chartRef.current?.getEchartsInstance();
    if (!chartInstance) return message.error("图表实例未加载");
    const url = chartInstance.getDataURL({ type: "png" });
    const a = document.createElement("a");
    a.href = url;
    a.download = `${charts[activeChart]?.title?.text || "chart"}.png`;
    a.click();
  };

  /** 📈 导出表格数据为 Excel */
  const exportExcel = () => {
    if (!tableData?.length) return message.warning("无数据可导出");
    const ws = XLSX.utils.json_to_sheet(tableData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
    XLSX.writeFile(wb, "data.xlsx");
  };

  /** ⏮️ 上一张 / 下一张 */
  const handlePrev = () => {
    setActiveChart((prev) => (prev === 0 ? charts.length - 1 : prev - 1));
  };
  const handleNext = () => {
    setActiveChart((prev) => (prev === charts.length - 1 ? 0 : prev + 1));
  };

  /** 监听容器尺寸变化 */
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;

    const checkReady = () => {
      if (el.clientWidth > 0 && el.clientHeight > 0) {
        setIsReady(true);
      } else {
        // 每100ms检查一次，直到有尺寸
        setTimeout(checkReady, 100);
      }
    };

    const observer = new ResizeObserver(() => {
      if (el.clientWidth > 0 && el.clientHeight > 0) {
        setIsReady(true);
        chartRef.current?.getEchartsInstance()?.resize();
      }
    });

    observer.observe(el);
    checkReady();

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const chartInstance = chartRef.current?.getEchartsInstance();
    if (chartInstance) chartInstance.resize();
  }, [activeChart, charts]);

  /** 🎨 动态按钮 */
  const renderButtons = () => {
    const buttons = [];

    if (activeTab === "chart") {
      buttons.push(
        <Tooltip title="导出图表" key="chart">
          <Button type="text" icon={<DownloadOutlined />} onClick={exportChartAsPng} />
        </Tooltip>
      );
    }

    if (activeTab === "sql") {
      buttons.push(
        <Tooltip title="复制SQL" key="sql">
          <Button type="text" icon={<CopyOutlined />} onClick={copySQL} />
        </Tooltip>
      );
    }

    if (activeTab === "table") {
      buttons.push(
        <Tooltip title="导出Excel" key="excel">
          <Button type="text" icon={<FileExcelOutlined />} onClick={exportExcel} />
        </Tooltip>
      );
    }

    return buttons;
  };

  return (
    <Card
      title="数据可视化"
      className="px-4 py-3 shadow-md rounded-2xl w-full max-w-[600px] overflow-hidden"
      extra={<div className="flex gap-1">{renderButtons()}</div>}
      style={{
        background: "#fff",
        borderRadius: "16px",
        marginBottom: "16px",
        height: "600px", // ✅ 固定高度
      }}
    >
      {/* <div className={`collapse-wrapper ${collapsed ? "collapsed" : ""}`}> */}
        <Tabs
          activeKey={activeTab}
          onChange={(key) => {
            setActiveTab(key);
            if (key === "chart") {
              setTimeout(() => {
                chartRef.current?.getEchartsInstance()?.resize();
              }, 100);
            }
          }}
          items={[
            {
              key: "table",
              label: "数据表",
              children: (
                <div className="w-full h-full flex flex-col">
                  <div className="flex-1 overflow-auto">
                    <Table
                      dataSource={tableData}
                      columns={
                        tableData?.length
                          ? Object.keys(tableData[0]).map((key) => ({
                              title: key,
                              dataIndex: key,
                              align: "center",
                              key,
                              sorter: (a, b) => {
                                const valA = a[key];
                                const valB = b[key];
                                if (!isNaN(valA) && !isNaN(valB)) {
                                  return Number(valA) - Number(valB);
                                }
                                return String(valA).localeCompare(String(valB), "zh");
                              },
                              filters: Array.from(
                                new Set(
                                  tableData
                                    .map((row:any) => row[key])
                                    .filter((v:any) => v !== null && v !== undefined)
                                )
                              ).map((v) => ({
                                text: String(v),
                                value: String(v),
                              })),
                              onFilter: (value, record) =>
                                String(record[key]).toLowerCase().includes(String(value).toLowerCase()),
                            }))
                          : []
                      }
                      pagination={{ pageSize: 10, position: ["bottomCenter"] }}
                      bordered
                      size="middle"
                      scroll={{
                        x: "max-content",
                        y: 350, // ✅ 固定纵向滚动高度，单位 px
                      }}
                      rowKey={getRowKey}
                      style={{ width: "100%" }}
                    />
                  </div>
                </div>
              ),
            },
            {
              key: "sql",
              label: "SQL",
              children: (
                <div
                  className="w-full h-full overflow-y-auto max-h-[400px] p-1"
                  style={{
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <pre className="bg-gray-50 p-3 rounded-lg text-sm min-w-[400px] w-full overflow-auto">
                    {isGeneratingSQL ? (
                      <div className="flex items-center space-x-2 text-gray-500">
                        <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                        <span>正在生成 SQL...</span>
                      </div>
                    ) : (
                      sql || "无 SQL 内容"
                    )}
                  </pre>
                </div>
              ),
            },
            {
              key: "chart",
              label: "图表",
              children: (
                <div
                  ref={containerRef}
                  className="flex flex-col items-center w-full h-full" // ✅ 添加高度控制
                >
                  {/* ✅ 滚动区域：只包含图表本体 */}
                  <div className="chart-scrollbar overflow-x-auto w-full flex justify-center h-[400px]"> {/* ✅ 固定图表高度 */}
                    {isGeneratingCharts ? (
                      <div className="flex items-center justify-center text-gray-500 py-20 space-x-2">
                        <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                        <span>正在生成图表...</span>
                      </div>
                    ) :!charts?.length ? (
                      <div className="text-gray-400 py-20">暂无图表</div>
                    ) : !isReady && isGeneratingCharts ? (
                      <div className="flex items-center justify-center text-gray-500 py-20 space-x-2">
                        <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                        <span>正在加载图表...</span>
                      </div>
                    ) : 
                    (
                      <ReactECharts
                        ref={chartRef}
                        option={{
                          ...charts[activeChart],
                          title: {
                            ...charts[activeChart]?.title,
                            top: 6,
                            left: "center",
                          },
                          legend: {
                            ...charts[activeChart]?.legend,
                            top: 40,
                            left: "center",
                            orient: "horizontal",
                            type: "scroll"
                          },
                          grid: {
                            top: 100,
                            left: 30,
                            right: 30,
                            bottom: 48,
                            containLabel: true,
                          },
                        }}
                        style={{ width: "100%", height: "100%" }}
                        notMerge
                        lazyUpdate
                        opts={{ renderer: "canvas" }}
                      />
                    )}
                  </div>
 
                  {/* ✅ 按钮放在滚动容器外部，始终固定在下方 */}
                  {charts?.length ? (
                    <div className="flex items-center justify-center gap-4 mt-4">
                      <Button
                        type="default"
                        shape="circle"
                        icon={<LeftOutlined />}
                        onClick={handlePrev}
                        disabled={!charts || charts.length <= 1}
                      />
                      <span className="text-base font-semibold">
                        {charts?.length ? `${activeChart + 1} / ${charts.length}` : "-"}
                      </span>
                      <Button
                        type="default"
                        shape="circle"
                        icon={<RightOutlined />}
                        onClick={handleNext}
                        disabled={!charts || charts.length <= 1}
                      />
                    </div>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      {/* </div> */}
    </Card>
  );
}