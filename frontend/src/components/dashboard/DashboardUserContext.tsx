"use client";

import { createContext, useContext } from "react";
import { User } from "@/types";

const DashboardUserContext = createContext<User | null>(null);

export function DashboardUserProvider({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  return (
    <DashboardUserContext.Provider value={user}>
      {children}
    </DashboardUserContext.Provider>
  );
}

export function useDashboardUser(): User {
  const user = useContext(DashboardUserContext);
  if (!user) {
    throw new Error("useDashboardUser must be used within DashboardShell");
  }
  return user;
}
