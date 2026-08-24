import { useEffect, useState } from "react";
import type { WebsocketProvider } from "y-websocket";

export interface PresenceIndicatorProps {
  provider: WebsocketProvider;
}

interface AwarenessUser {
  name: string;
  color: string;
}

export function PresenceIndicator({ provider }: PresenceIndicatorProps) {
  const [users, setUsers] = useState<Array<{ clientId: number; user: AwarenessUser }>>([]);

  useEffect(() => {
    const awareness = provider.awareness;

    const readStates = () => {
      const states = awareness.getStates() as Map<number, { user?: AwarenessUser }>;
      const nextUsers: Array<{ clientId: number; user: AwarenessUser }> = [];
      states.forEach((state, clientId) => {
        if (state.user) {
          nextUsers.push({ clientId, user: state.user });
        }
      });
      setUsers(nextUsers);
    };

    readStates();
    awareness.on("change", readStates);

    return () => {
      if (typeof awareness.off === "function") {
        awareness.off("change", readStates);
      }
    };
  }, [provider]);

  return (
    <div aria-label="presence-indicator">
      {users.map(({ clientId, user }) => (
        <div key={clientId} data-testid={`presence-dot-${clientId}`}>
          <span
            data-testid={`dot-color-${clientId}`}
            style={{
              backgroundColor: user.color,
              borderRadius: "50%",
              display: "inline-block",
              width: "10px",
              height: "10px",
            }}
          />
          <span>{user.name}</span>
        </div>
      ))}
    </div>
  );
}
