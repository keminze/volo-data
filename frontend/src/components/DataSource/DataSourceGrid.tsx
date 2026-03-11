"use client"

import { useEffect } from "react"
import { DataSourceCard } from "./DataSourceCard"
import { NewDataSourceCard } from "./NewDataSourceCard"
import { useDataSourceStore } from "@/store/dataSourceStore"
import {useExampleDataSourceStore} from "@/store/dataSourceStore"
export function DataSourceGrid() {
  const { dataSources, loading, fetchDataSources } = useDataSourceStore()
  const { exampleDataSources, fetchExampleDataSources } = useExampleDataSourceStore()

  useEffect(() => {
    fetchDataSources()
    fetchExampleDataSources()

    // ✅ 监听刷新事件
    const handleRefresh = () => {
      console.log("收到刷新事件，重新加载数据源")
      fetchDataSources()
    }

    window.addEventListener("datasource:refresh", handleRefresh)
    return () => window.removeEventListener("datasource:refresh", handleRefresh)
  }, [fetchDataSources])

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64 text-gray-500">
        加载中...
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <NewDataSourceCard />
      {exampleDataSources.map((ds) => (
        <DataSourceCard key={ds.id} dataSource={ds} isExample={true} />
      ))}
      {dataSources.map((ds) => (
        <DataSourceCard key={ds.id} dataSource={ds} isExample={false} />
      ))}
    </div>
  )
}
