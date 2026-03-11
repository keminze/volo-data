"use client";

import { useEffect, useState } from "react";
import { DataSourceNavbar } from "./DataSourceNavbar";
import { DataSourceGrid } from "./DataSourceGrid";
import type { DataSource } from "./types";
// import { listConnections } from "@/lib/api/connections"; // ✅ 引入封装的 API
import { Loader2 } from "lucide-react";
// import {useDataSourceStore} from "@/store/dataSourceStore";
export default function DataSource() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);


  // ✅ 渲染逻辑
  return (
    <div className="flex flex-col w-full h-full bg-white py-8 px-8">
      <DataSourceNavbar
        search={search}
        onSearchChange={setSearch}
        filter={filter}
        onFilterChange={setFilter}
      />

      <DataSourceGrid />
      {/* )} */}
    </div>
  );
}
