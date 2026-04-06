import { ArtifactImage, type License } from "./artifact-image";

interface ArtifactCardProps {
  id: string;
  title?: string;
  objectType?: string;
  period?: string;
  dynasty?: string;
  rulerDisplayName?: string;
  dateDisplay?: string;
  originSiteRaw?: string;
  originSiteDisplayName?: string;
  sourceMuseum: string;
  sourceUrl: string;
  imageUrl?: string;
  thumbnailUrl?: string;
  license: License;
}

const MUSEUM_LABELS: Record<string, string> = {
  met: "Metropolitan Museum of Art",
  brooklyn: "Brooklyn Museum",
  harvard: "Harvard Art Museums",
};

export function ArtifactCard({
  title,
  objectType,
  period,
  dynasty,
  rulerDisplayName,
  dateDisplay,
  originSiteRaw,
  originSiteDisplayName,
  sourceMuseum,
  sourceUrl,
  imageUrl,
  thumbnailUrl,
  license,
}: ArtifactCardProps) {
  const siteName = originSiteDisplayName ?? originSiteRaw;

  return (
    <div className="group rounded-lg border border-gray-200 bg-white overflow-hidden hover:shadow-md transition-shadow">
      <div className="aspect-square bg-gray-50">
        <ArtifactImage
          imageUrl={imageUrl}
          thumbnailUrl={thumbnailUrl}
          license={license}
          title={title ?? "Untitled artifact"}
          sourceUrl={sourceUrl}
          sourceMuseum={MUSEUM_LABELS[sourceMuseum] ?? sourceMuseum}
          width={400}
          height={400}
          className="w-full h-full"
        />
      </div>
      <div className="p-3">
        <h3 className="text-sm font-medium text-gray-900 line-clamp-2">
          {title ?? "Untitled"}
        </h3>
        {objectType && (
          <p className="text-xs text-gray-500 mt-1">{objectType}</p>
        )}
        <div className="flex flex-wrap gap-x-2 gap-y-1 mt-2">
          {dynasty && (
            <span className="text-xs text-gray-600">{dynasty}</span>
          )}
          {rulerDisplayName && (
            <span className="text-xs text-gray-600">{rulerDisplayName}</span>
          )}
          {!dynasty && !rulerDisplayName && period && (
            <span className="text-xs text-gray-600">{period}</span>
          )}
          {dateDisplay && (
            <span className="text-xs text-gray-400">{dateDisplay}</span>
          )}
        </div>
        {siteName && (
          <p className="text-xs text-amber-700 mt-1">{siteName}</p>
        )}
        <p className="text-xs text-gray-400 mt-1">
          {MUSEUM_LABELS[sourceMuseum] ?? sourceMuseum}
        </p>
      </div>
    </div>
  );
}
