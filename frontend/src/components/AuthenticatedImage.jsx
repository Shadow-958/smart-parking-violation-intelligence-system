import { useEffect, useState } from "react";
import apiClient from "../lib/apiClient";

/**
 * Renders a complaint photo that lives behind JWT auth. A plain
 * `<img src="...">` can't send an Authorization header, so this fetches
 * the bytes through apiClient (which does attach the header) and hands
 * the browser an object URL instead.
 */
export default function AuthenticatedImage({ imageId, alt, className, onLoad }) {
  const [objectUrl, setObjectUrl] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let currentUrl = null;
    let cancelled = false;

    apiClient
      .get(`/api/complaints/images/${imageId}/file`, { responseType: "blob" })
      .then((response) => {
        if (cancelled) return;
        currentUrl = URL.createObjectURL(response.data);
        setObjectUrl(currentUrl);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => {
      cancelled = true;
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [imageId]);

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-asphalt/5 text-sm text-ink/50 ${className || ""}`}>
        Image unavailable
      </div>
    );
  }

  if (!objectUrl) {
    return <div className={`animate-pulse bg-asphalt/10 ${className || ""}`} />;
  }

  return <img src={objectUrl} alt={alt} className={className} onLoad={onLoad} />;
}
