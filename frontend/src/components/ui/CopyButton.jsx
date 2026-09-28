import React, { useState } from "react";
import { Button } from "./Button.jsx";

export function CopyButton({
  text,
  label = "Copy",
  copiedLabel = "Copied",
  variant = "default",
  size = "default",
  className = "",
  onCopied = null,
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (onCopied) onCopied();
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <Button
      variant={variant}
      size={size}
      className={className}
      onClick={handleCopy}
    >
      {copied ? copiedLabel : label}
    </Button>
  );
}
