import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  type ReactNode,
  type Dispatch,
  type SetStateAction,
} from "react";

export type DraftFacts = Record<string, string | boolean>;
export type ConfirmedFacts = Record<string, number | boolean>;
type Workspace = {
  scope?: string;
  facts: DraftFacts;
  setFacts: Dispatch<SetStateAction<DraftFacts>>;
  confirmedFacts: ConfirmedFacts | null;
  setConfirmedFacts: Dispatch<SetStateAction<ConfirmedFacts | null>>;
};
const WorkspaceContext = createContext<Workspace | null>(null);

export function FinancialWorkspace({ children, scope }: { children: ReactNode; scope?: string }) {
  const [facts, setFacts] = useState<DraftFacts>({ bills_complete: false, debt_complete: false });
  const [confirmedFacts, setConfirmedFacts] = useState<ConfirmedFacts | null>(null);
  const previousScope = useRef(scope);
  useEffect(() => {
    if (previousScope.current && scope && previousScope.current !== scope) {
      setFacts({ bills_complete: false, debt_complete: false });
      setConfirmedFacts(null);
    }
    previousScope.current = scope;
  }, [scope]);
  return (
    <WorkspaceContext.Provider
      value={{ scope, facts, setFacts, confirmedFacts, setConfirmedFacts }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useFinancialWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("Financial workspace is unavailable");
  return value;
}
