import type { ReactNode } from "react";

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={index}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={index}>{part}</span>
    ),
  );
}

export default function ChatRichText({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  for (let index = 0; index < lines.length; ) {
    const line = lines[index].trim();
    if (!line) {
      index += 1;
    } else if (line.startsWith("### ")) {
      blocks.push(<h3 key={`h-${index}`}>{inline(line.slice(4))}</h3>);
      index += 1;
    } else if (line.startsWith("- ")) {
      const items: ReactNode[] = [];
      while (index < lines.length && lines[index].trim().startsWith("- ")) {
        items.push(<li key={index}>{inline(lines[index].trim().slice(2))}</li>);
        index += 1;
      }
      blocks.push(<ul key={`l-${index}`}>{items}</ul>);
    } else {
      blocks.push(<p key={`p-${index}`}>{inline(line)}</p>);
      index += 1;
    }
  }
  return <div className="chat-rich-text">{blocks}</div>;
}
