"use client";

export default function DiffViewer({ diff }: { diff: string }) {
  if (!diff.trim())
    return (
      <div className="diff-empty">
        No code changes were made during this investigation.
      </div>
    );
  const filename = diff.match(/^\+\+\+ (?:b\/)?(.+)$/m)?.[1];
  return (
    <div className="diff-view">
      <div className="diff-header">{filename || "Patch diff"}</div>
      <div
        className="diff-scroll"
        tabIndex={0}
        role="region"
        aria-label="Patch diff, scroll horizontally to inspect long lines"
      >
        <pre>
          <code>
            {diff.split("\n").map((line, index) => {
              const kind =
                line.startsWith("+++") || line.startsWith("---")
                  ? "meta"
                  : line.startsWith("+")
                    ? "add"
                    : line.startsWith("-")
                      ? "remove"
                      : line.startsWith("@@")
                        ? "hunk"
                        : "context";
              return (
                <span key={index} className={`diff-line diff-${kind}`}>
                  {line || " "}
                </span>
              );
            })}
          </code>
        </pre>
      </div>
    </div>
  );
}
