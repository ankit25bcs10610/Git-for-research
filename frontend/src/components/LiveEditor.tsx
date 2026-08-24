import { useEffect, useRef, useState, type ChangeEvent } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";

export interface LiveEditorProps {
  roomId: string;
  wsUrl: string;
  onReady?: (ydoc: Y.Doc, provider: WebsocketProvider) => void;
}

export function LiveEditor({ roomId, wsUrl, onReady }: LiveEditorProps) {
  const [text, setText] = useState("");
  const ydocRef = useRef<Y.Doc | null>(null);
  const ytextRef = useRef<Y.Text | null>(null);

  useEffect(() => {
    const ydoc = new Y.Doc();
    const provider = new WebsocketProvider(wsUrl, roomId, ydoc);
    const ytext = ydoc.getText("content");

    ydocRef.current = ydoc;
    ytextRef.current = ytext;
    setText(ytext.toString());

    const handleUpdate = () => {
      setText(ytext.toString());
    };
    ytext.observe(handleUpdate);

    if (onReady) {
      onReady(ydoc, provider);
    }

    return () => {
      ytext.unobserve(handleUpdate);
      provider.destroy();
      ydoc.destroy();
    };
  }, [roomId, wsUrl, onReady]);

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = event.target.value;
    const ytext = ytextRef.current;
    const ydoc = ydocRef.current;
    if (!ytext || !ydoc) {
      return;
    }
    ydoc.transact(() => {
      ytext.delete(0, ytext.length);
      ytext.insert(0, newValue);
    });
  };

  return <textarea value={text} onChange={handleChange} aria-label="live-editor" />;
}
