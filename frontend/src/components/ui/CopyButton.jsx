import React, { useState } from "react";
import { Button } from "./Button.jsx";
import { copyText } from "../../lib/clipboard.js";

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
    const success = await copyText(text);
    if (success) {
      setCopied(true);
      if (onCopied) onCopied();
      setTimeout(() => setCopied(false), 2000);
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
