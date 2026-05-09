"use client";
import { useState, useRef, useEffect } from "react";
import ReactECharts from "echarts-for-react";
import { Card, Button } from "antd";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";

export default function AgentChartCard({ charts }: { charts: any[] }) {
  const [activeChart, setActiveChart] = useState(0);
  const [isReady, setIsReady] = useState(false);
  const chartRef = useRef<ReactECharts | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;

    const checkReady = () => {
      if (el.clientWidth > 0 && el.clientHeight > 0) {
        setIsReady(true);
      } else {
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

  const handlePrev = () => {
    setActiveChart((prev) => (prev === 0 ? charts.length - 1 : prev - 1));
  };
  const handleNext = () => {
    setActiveChart((prev) => (prev === charts.length - 1 ? 0 : prev + 1));
  };

  if (!charts || charts.length === 0) return null;

  return (
    <Card
      title="图表"
      className="px-4 py-3 shadow-md rounded-2xl w-full max-w-[600px] overflow-hidden mb-3"
      style={{
        background: "#fff",
        borderRadius: "16px",
        height: "600px",
      }}
    >
      <div
        ref={containerRef}
        className="flex flex-col items-center w-full h-full"
      >
        <div className="overflow-x-auto w-full flex justify-center h-[400px]">
          {!isReady ? (
            <div className="flex items-center justify-center text-gray-500 py-20 space-x-2">
              <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              <span>正在加载图表...</span>
            </div>
          ) : (
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
                  type: "scroll",
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

        {charts.length > 1 && (
          <div className="flex items-center justify-center gap-4 mt-4">
            <Button
              type="default"
              shape="circle"
              icon={<LeftOutlined />}
              onClick={handlePrev}
            />
            <span className="text-base font-semibold">
              {activeChart + 1} / {charts.length}
            </span>
            <Button
              type="default"
              shape="circle"
              icon={<RightOutlined />}
              onClick={handleNext}
            />
          </div>
        )}
      </div>
    </Card>
  );
}
