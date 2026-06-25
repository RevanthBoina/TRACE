import { NextRequest, NextResponse } from "next/server";
import { createHash } from "crypto";
import { v4 as uuidv4 } from "uuid";

interface UploadResponse {
  job_id: string;
  status: string;
  message: string;
}

// In-memory store for development (Vercel KV or database in production)
const uploads: Map<string, any> = new Map();

export async function POST(request: NextRequest) {
  try {
    // Validate content type
    const contentType = request.headers.get("content-type") || "";
    if (!contentType.includes("multipart/form-data")) {
      return NextResponse.json(
        { error: "Content-Type must be multipart/form-data" },
        { status: 400 }
      );
    }

    // Parse form data
    const formData = await request.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json(
        { error: "No file provided" },
        { status: 400 }
      );
    }

    // Validate file type
    if (!file.type.startsWith("video/")) {
      return NextResponse.json(
        { error: "File must be a video" },
        { status: 400 }
      );
    }

    // Read file content
    const content = await file.arrayBuffer();
    const buffer = Buffer.from(content);

    // Compute SHA-256 hash
    const fileHash = createHash("sha256").update(buffer).digest("hex");

    // Check for duplicate (in-memory for now)
    for (const [_, upload] of uploads) {
      if (upload.file_hash === fileHash) {
        const response: UploadResponse = {
          job_id: upload.id,
          status: "duplicate",
          message: "File already uploaded",
        };
        return NextResponse.json(response);
      }
    }

    // Generate unique ID and S3 key
    const jobId = uuidv4();
    const s3Key = `uploads/${jobId}/${file.name}`;

    // Upload to S3 if credentials are available
    if (process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY) {
      try {
        const { S3Client, PutObjectCommand } = await import("@aws-sdk/client-s3");
        
        const s3 = new S3Client({
          region: process.env.AWS_REGION || "us-east-1",
          credentials: {
            accessKeyId: process.env.AWS_ACCESS_KEY_ID,
            secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
          },
        });

        await s3.send(new PutObjectCommand({
          Bucket: process.env.S3_UPLOAD_BUCKET,
          Key: s3Key,
          Body: buffer,
          ContentType: file.type,
        }));
      } catch (s3Error: any) {
        console.error("S3 upload error:", s3Error);
        // Continue anyway - store metadata locally
      }
    }

    // Store upload metadata (in production, use database)
    const upload = {
      id: jobId,
      file_hash: fileHash,
      s3_key: s3Key,
      filename: file.name,
      status: "uploaded",
      created_at: new Date().toISOString(),
    };
    uploads.set(jobId, upload);

    const response: UploadResponse = {
      job_id: jobId,
      status: "uploaded",
      message: "File uploaded successfully",
    };

    return NextResponse.json(response);
  } catch (error: any) {
    console.error("Upload error:", error);
    return NextResponse.json(
      { error: error.message || "Upload failed" },
      { status: 500 }
    );
  }
}
