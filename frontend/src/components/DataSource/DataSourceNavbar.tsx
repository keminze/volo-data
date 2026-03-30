"use client";

import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();

  return (
    <div className="flex items-center justify-between mb-6">
      <h2 className="text-xl font-semibold">{t("dataSources.title")}</h2>
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder={t("dataSources.search")}
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-8 w-48"
          />
        </div>
        <Select onValueChange={(val) => onFilterChange(val === "all" ? null : val)} value={filter || "all"}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder={t("dataSources.filter")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
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
