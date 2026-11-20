import type { ErrorCode } from "./types";
export class ApiError extends Error {
  code: ErrorCode | "network_error";
  status: number;
  constructor(code: ErrorCode | "network_error", message: string, status = 0) {
    super(message); this.code = code; this.status = status;
  }
}
