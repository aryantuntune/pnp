"use client";

import {
  formatItemWiseForPrint,
  ItemWiseSummaryRow,
  ItemWiseSummaryMetaData,
} from "@/lib/print-itemwise-summary";

interface ItemWisePrintViewProps {
  reportData: ItemWiseSummaryRow[];
  metaData: ItemWiseSummaryMetaData;
}

/**
 * Renders a monospace preview of the thermal-print output and provides a
 * browser Print button.  Wrap this in a dialog or panel as needed.
 *
 * At print time, every element except this component is hidden via
 * @media print so window.print() outputs only the receipt.
 */
export function ItemWisePrintView({
  reportData,
  metaData,
}: ItemWisePrintViewProps) {
  const text = formatItemWiseForPrint(reportData, metaData);

  const handlePrint = () => window.print();

  return (
    <>
      <style>{`
        @media print {
          body > *:not(#thermal-print-root) { display: none !important; }
          #thermal-print-root {
            display: block !important;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: #fff;
            z-index: 9999;
          }
          .thermal-print-btn { display: none !important; }
          @page { size: 80mm auto; margin: 0; }
          pre {
            font-family: monospace;
            font-size: 10px;
            line-height: 1.2;
            width: 80mm;
            white-space: pre;
            font-weight: 700;
            color: #000;
          }
        }
      `}</style>

      <div id="thermal-print-root">
        <pre
          style={{ fontFamily: "monospace", fontSize: "10px", lineHeight: "1.2" }}
          className="font-bold whitespace-pre bg-white p-4 border border-gray-300 rounded overflow-x-auto max-w-xs"
        >
          {text}
        </pre>

        <button
          className="thermal-print-btn mt-3 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 active:bg-blue-800"
          onClick={handlePrint}
        >
          Print
        </button>
      </div>
    </>
  );
}
