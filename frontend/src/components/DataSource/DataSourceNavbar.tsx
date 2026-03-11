import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search } from "lucide-react"

interface Props {
  search: string
  onSearchChange: (value: string) => void
  filter: string | null
  onFilterChange: (value: string | null) => void
}

export function DataSourceNavbar({ search, onSearchChange, filter, onFilterChange }: Props) {
  return (
    <div className="flex items-center justify-between mb-6">
      <h2 className="text-xl font-semibold">我的数据源</h2>
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="搜索数据源..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-8 w-48"
          />
        </div>
        <Select onValueChange={(val) => onFilterChange(val === "all" ? null : val)} value={filter || "all"}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="筛选类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="sqlite">SQLite</SelectItem>
            <SelectItem value="mysql">MySQL</SelectItem>
            <SelectItem value="csv">CSV</SelectItem>
            <SelectItem value="excel">Excel</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
