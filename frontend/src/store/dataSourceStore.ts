import { create } from "zustand"
import type { DataSource } from "@/components/DataSource/types"
import { listConnections } from "@/lib/api/connections"
import { getOrCreateUUID } from "@/lib/utils"


interface DataSourceStore {
  dataSources: DataSource[]
  loading: boolean
  fetchDataSources: () => Promise<void>
  setDataSources: (data: DataSource[]) => void
}

interface ExampleDataSourceStore {
  exampleDataSources: DataSource[]
  loading: boolean
  fetchExampleDataSources: () => Promise<void>
  setExampleDataSources: (data: DataSource[]) => void
}

export const useDataSourceStore = create<DataSourceStore>((set) => ({
  dataSources: [],
  loading: false,

  // ✅ 拉取数据源列表
  fetchDataSources: async () => {
    try {
      set({ loading: true })
      const res = await listConnections(getOrCreateUUID())
      set({ dataSources: res || [] })
    } catch (err) {
      console.error("❌ 获取数据源失败:", err)
    } finally {
      set({ loading: false })
    }
  },

  // ✅ 手动更新数据源（比如删除后刷新）
  setDataSources: (data) => set({ dataSources: data }),
}))

export const useExampleDataSourceStore = create<ExampleDataSourceStore>((set) => ({
  exampleDataSources: [],
  loading: false,

  // ✅ 拉取数据源列表
  fetchExampleDataSources: async () => {
    try {
      set({ loading: true })
      const res = await listConnections("example")
      set({ exampleDataSources: res || [] })
    } catch (err) {
      console.error("❌ 获取数据源失败:", err)
    } finally {
      set({ loading: false })
    }
  },

  // ✅ 手动更新数据源（比如删除后刷新）
  setExampleDataSources: (data) => set({ exampleDataSources: data }),
}))