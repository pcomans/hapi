import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

afterEach(cleanup);

import { ArtifactImage } from "./artifact-image";

const BASE_PROPS = {
  title: "Test Artifact",
  sourceUrl: "https://example.com/artifact/1",
  sourceMuseum: "Test Museum",
  width: 300,
  height: 300,
};

describe("ArtifactImage", () => {
  describe("CC0 license (unrestricted)", () => {
    it("embeds the image directly", () => {
      render(
        <ArtifactImage
          {...BASE_PROPS}
          imageUrl="https://example.com/image.jpg"
          thumbnailUrl={null}
          license="cc0"
        />,
      );
      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("alt", "Test Artifact");
    });

    it("does not show attribution", () => {
      render(
        <ArtifactImage
          {...BASE_PROPS}
          imageUrl="https://example.com/image.jpg"
          thumbnailUrl={null}
          license="cc0"
        />,
      );
      expect(screen.queryByTestId("image-attribution")).not.toBeInTheDocument();
    });
  });

  describe("CC BY-NC-ND license (embed with attribution)", () => {
    it("embeds the image", () => {
      render(
        <ArtifactImage
          {...BASE_PROPS}
          imageUrl="https://example.com/image.jpg"
          thumbnailUrl={null}
          license="cc-by-nc-nd"
        />,
      );
      expect(screen.getByRole("img")).toBeInTheDocument();
    });

    it("shows attribution with license label", () => {
      render(
        <ArtifactImage
          {...BASE_PROPS}
          imageUrl="https://example.com/image.jpg"
          thumbnailUrl={null}
          license="cc-by-nc-nd"
        />,
      );
      const attribution = screen.getByTestId("image-attribution");
      expect(attribution).toHaveTextContent("Test Museum");
      expect(attribution).toHaveTextContent("CC BY-NC-ND");
    });
  });

  describe("restricted license (no embed)", () => {
    it("shows placeholder with link to source", () => {
      render(
        <ArtifactImage
          {...BASE_PROPS}
          imageUrl="https://example.com/image.jpg"
          thumbnailUrl={null}
          license="restricted"
        />,
      );
      expect(screen.queryByRole("img")).not.toBeInTheDocument();
      expect(screen.getByTestId("image-placeholder")).toBeInTheDocument();
      expect(screen.getByText("View on Test Museum")).toBeInTheDocument();
    });
  });

  describe("unknown license (no embed)", () => {
    it("shows placeholder even when image URL exists", () => {
      render(
        <ArtifactImage
          {...BASE_PROPS}
          imageUrl="https://example.com/image.jpg"
          thumbnailUrl={null}
          license="unknown"
        />,
      );
      expect(screen.queryByRole("img")).not.toBeInTheDocument();
      expect(screen.getByTestId("image-placeholder")).toBeInTheDocument();
    });
  });

  describe("no image URL", () => {
    it("shows placeholder regardless of license", () => {
      render(
        <ArtifactImage
          {...BASE_PROPS}
          imageUrl={null}
          thumbnailUrl={null}
          license="cc0"
        />,
      );
      expect(screen.queryByRole("img")).not.toBeInTheDocument();
      expect(screen.getByTestId("image-placeholder")).toBeInTheDocument();
    });
  });

  describe("thumbnail preference", () => {
    it("uses thumbnail URL when available", () => {
      render(
        <ArtifactImage
          {...BASE_PROPS}
          imageUrl="https://example.com/full.jpg"
          thumbnailUrl="https://example.com/thumb.jpg"
          license="cc0"
        />,
      );
      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("src", "https://example.com/thumb.jpg");
    });
  });
});
