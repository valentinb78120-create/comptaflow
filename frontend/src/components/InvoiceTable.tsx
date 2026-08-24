import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from "@tanstack/react-table";
import type { Invoice } from "../types/invoice";
import { StatusBadge } from "./StatusBadge";
import { formatAmount, formatDate } from "../lib/utils";

interface Props {
  invoices: Invoice[];
  onSelect: (invoice: Invoice) => void;
}

const col = createColumnHelper<Invoice>();

const columns = [
  col.accessor("original_filename", {
    header: "Fichier",
    cell: (i) => (
      <span className="font-medium text-gray-900 truncate max-w-[180px] block">
        {i.getValue()}
      </span>
    ),
  }),
  col.accessor("vendor_name", {
    header: "Fournisseur",
    cell: (i) => i.getValue() ?? <span className="text-gray-400">—</span>,
  }),
  col.accessor("invoice_date", {
    header: "Date facture",
    cell: (i) => formatDate(i.getValue()),
  }),
  col.accessor("amount_ttc", {
    header: "Montant TTC",
    cell: (i) => (
      <span className="font-mono">{formatAmount(i.getValue())}</span>
    ),
  }),
  col.accessor("pcg_account", {
    header: "Compte PCG",
    cell: (i) => {
      const account = i.getValue();
      const label = i.row.original.pcg_label;
      if (!account) return <span className="text-gray-400">Non catégorisé</span>;
      return (
        <span title={label ?? undefined} className="font-mono text-sm">
          {account}
        </span>
      );
    },
  }),
  col.accessor("status", {
    header: "Statut",
    cell: (i) => <StatusBadge status={i.getValue()} />,
  }),
  col.accessor("ocr_confidence", {
    header: "Confiance",
    cell: (i) => {
      const v = i.getValue();
      if (v == null) return <span className="text-gray-400">—</span>;
      const pct = Math.round(v * 100);
      const color = pct >= 80 ? "text-green-600" : pct >= 50 ? "text-amber-600" : "text-red-600";
      return <span className={`font-mono text-sm ${color}`}>{pct}%</span>;
    },
  }),
];

export function InvoiceTable({ invoices, onSelect }: Props) {
  const table = useReactTable({
    data: invoices,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full text-sm text-left">
        <thead className="bg-gray-50 border-b border-gray-200">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th key={h.id} className="px-4 py-3 font-medium text-gray-600 whitespace-nowrap">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
              <th className="px-4 py-3 font-medium text-gray-600">Actions</th>
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-gray-100">
          {table.getRowModel().rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length + 1} className="px-4 py-8 text-center text-gray-400">
                Aucune facture — uploadez un fichier pour commencer
              </td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3 text-gray-700">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
                <td className="px-4 py-3">
                  <button
                    onClick={() => onSelect(row.original)}
                    className="text-brand-600 hover:text-brand-700 text-sm font-medium"
                  >
                    Vérifier
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
