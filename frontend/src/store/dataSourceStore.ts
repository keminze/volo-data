import { create } from "zustand"
import type { DataSource } from "@/components/DataSource/types"
import { listConnections } from "@/lib/api/connections"


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

  fetchDataSources: async () => {
    try {
      set({ loading: true })
      const res = await listConnections()
      set({ dataSources: res || [] })
    } catch (err) {
      console.error("获取数据源失败:", err)
    } finally {
      set({ loading: false })
    }
  },

  setDataSources: (data) => set({ dataSources: data }),
}))

export const useExampleDataSourceStore = create<ExampleDataSourceStore>((set) => ({
  exampleDataSources: [],
  loading: false,

  fetchExampleDataSources: async () => {
    try {
      set({ loading: true })
      const res = await listConnections()
      set({ exampleDataSources: res || [] })
    } catch (err) {
      console.error("获取示例数据源失败:", err)
    } finally {
      set({ loading: false })
    }
  },

  setExampleDataSources: (data) => set({ exampleDataSources: data }),
}))