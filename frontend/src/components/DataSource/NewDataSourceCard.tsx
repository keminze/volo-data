"use client"

import { useState } from "react"
import { Plus } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { NewDataSourceDialog } from "./CreateDataSource"

export function NewDataSourceCard() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Card
        onClick={() => setOpen(true)}
        className="flex items-center justify-center cursor-pointer py-4 hover:shadow-lg transition-shadow duration-200 border-dashed border-2 border-gray-300 hover:border-primary"
      >
        <CardContent className="flex flex-col items-center justify-center text-center space-y-2 p-4">
          <div className="bg-primary/10 p-3 rounded-full">
            <Plus className="w-4 h-4 text-primary" />
          </div>
          <p className="text-sm text-gray-600 font-medium">新建数据源</p>
        </CardContent>
      </Card>

      <NewDataSourceDialog open={open} onOpenChange={setOpen} />
    </>
  )
}
