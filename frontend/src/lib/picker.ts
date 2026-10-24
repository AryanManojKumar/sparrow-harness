/** postMessage contract with the picker injected into /projects/{id}/preview. */

export const PICKER_CHANNEL = "sparrow";

export type PickedElement = {
  tag: string;
  text: string;
  ariaLabel: string | null;
  sectionId: string | null;
  selector: string;
  fileHint: string | null;
  rect: { top: number; left: number; width: number; height: number };
};

export type PickerMessage =
  | { channel: typeof PICKER_CHANNEL; type: "ready"; payload: null }
  | { channel: typeof PICKER_CHANNEL; type: "element-select"; payload: PickedElement }
  | { channel: typeof PICKER_CHANNEL; type: "element-clear"; payload: null };

export function parsePickerMessage(data: unknown): PickerMessage | null {
  if (!data || typeof data !== "object") return null;
  const d = data as Record<string, unknown>;
  if (d.channel !== PICKER_CHANNEL || typeof d.type !== "string") return null;
  if (d.type === "ready" || d.type === "element-clear") {
    return { channel: PICKER_CHANNEL, type: d.type, payload: null };
  }
  if (d.type === "element-select" && d.payload && typeof d.payload === "object") {
    const p = d.payload as PickedElement;
    return { channel: PICKER_CHANNEL, type: "element-select", payload: p };
  }
  return null;
}

/** Body of POST /projects/{id}/edit — snake_case to match the API. */
export function toEditElement(el: PickedElement) {
  return {
    tag: el.tag,
    text: el.text,
    aria_label: el.ariaLabel,
    section_id: el.sectionId,
    selector: el.selector,
    file_hint: el.fileHint,
  };
}
