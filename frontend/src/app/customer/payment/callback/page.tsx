"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import CustomerLayout from "@/components/customer/CustomerLayout";
import { CheckCircle, XCircle, ArrowLeft, Loader2 } from "lucide-react";

function PaymentCallbackContent() {
  const params = useSearchParams();
  const status = params.get("status");
  const bookingId = params.get("booking_id");
  const error = params.get("error");

  const isSuccess = status === "success";

  return (
    <CustomerLayout>
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <div className="bg-white rounded-3xl shadow-xl border border-slate-100 p-8">
          {isSuccess ? (
            <>
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <h1 className="text-2xl font-bold text-slate-800 mb-2">
                Payment Successful!
              </h1>
              <p className="text-slate-500 mb-8">
                Your booking has been confirmed. You will receive a confirmation
                email shortly.
              </p>
              {bookingId && (
                <Link
                  href={`/customer/history/${bookingId}`}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-sky-600 text-white font-semibold hover:bg-sky-700 transition-colors"
                >
                  View Booking & Download Ticket
                </Link>
              )}
            </>
          ) : (
            <>
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-100 flex items-center justify-center">
                <XCircle className="w-10 h-10 text-red-600" />
              </div>
              <h1 className="text-2xl font-bold text-slate-800 mb-2">
                Payment Failed
              </h1>
              <p className="text-slate-500 mb-2">
                {error || "Your payment could not be processed. Please try again."}
              </p>
              <p className="text-sm text-slate-400 mb-8">
                No money has been deducted from your account. If any amount was
                debited, it will be refunded within 5-7 business days.
              </p>
              {bookingId ? (
                <Link
                  href={`/customer/history/${bookingId}`}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-sky-600 text-white font-semibold hover:bg-sky-700 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Retry Payment
                </Link>
              ) : (
                <Link
                  href="/customer/history"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-sky-600 text-white font-semibold hover:bg-sky-700 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Go to My Bookings
                </Link>
              )}
            </>
          )}
        </div>
      </div>
    </CustomerLayout>
  );
}

export default function PaymentCallbackPage() {
  return (
    <Suspense
      fallback={
        <CustomerLayout>
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
          </div>
        </CustomerLayout>
      }
    >
      <PaymentCallbackContent />
    </Suspense>
  );
}
