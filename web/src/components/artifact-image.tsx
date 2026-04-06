import Image from "next/image";

export type License =
  | "cc0"
  | "cc-by"
  | "cc-by-nc"
  | "cc-by-nc-nd"
  | "cc-by-nc-sa"
  | "non-commercial-educational"
  | "restricted"
  | "unknown";

interface ArtifactImageProps {
  imageUrl: string | null | undefined;
  thumbnailUrl: string | null | undefined;
  license: License;
  title: string;
  sourceUrl: string;
  sourceMuseum: string;
  width?: number;
  height?: number;
  className?: string;
}

const LICENSE_LABELS: Partial<Record<License, string>> = {
  "cc-by": "CC BY",
  "cc-by-nc": "CC BY-NC",
  "cc-by-nc-nd": "CC BY-NC-ND",
  "cc-by-nc-sa": "CC BY-NC-SA",
  "non-commercial-educational": "Non-commercial educational use",
};

function canEmbed(license: License): boolean {
  return [
    "cc0",
    "cc-by",
    "cc-by-nc",
    "cc-by-nc-nd",
    "cc-by-nc-sa",
    "non-commercial-educational",
  ].includes(license);
}

function needsAttribution(license: License): boolean {
  return license !== "cc0";
}

export function ArtifactImage({
  imageUrl,
  thumbnailUrl,
  license,
  title,
  sourceUrl,
  sourceMuseum,
  width = 400,
  height = 400,
  className,
}: ArtifactImageProps) {
  const src = thumbnailUrl ?? imageUrl;

  if (!src) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 text-gray-400 ${className ?? ""}`}
        style={{ width, height }}
        data-testid="image-placeholder"
      >
        <span className="text-center p-4 text-sm">No image available</span>
      </div>
    );
  }

  if (!canEmbed(license)) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 text-gray-500 ${className ?? ""}`}
        style={{ width, height }}
        data-testid="image-restricted"
      >
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-center p-4 hover:text-gray-700"
        >
          <span className="block text-sm">View on {sourceMuseum}</span>
          <span className="block text-xs mt-1">Image not licensed for embedding</span>
        </a>
      </div>
    );
  }

  return (
    <figure className={className}>
      <Image
        src={src}
        alt={title}
        width={width}
        height={height}
        className="object-contain"
        unoptimized
      />
      {needsAttribution(license) && (
        <figcaption className="text-xs text-gray-500 mt-1" data-testid="image-attribution">
          <a href={sourceUrl} target="_blank" rel="noopener noreferrer">
            {sourceMuseum}
          </a>
          {LICENSE_LABELS[license] && ` · ${LICENSE_LABELS[license]}`}
        </figcaption>
      )}
    </figure>
  );
}
