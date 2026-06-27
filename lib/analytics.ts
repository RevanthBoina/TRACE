/**
 * TRACE Analytics Utility
 * 
 * Provides consistent tracking for user actions and events.
 * Uses Vercel Analytics custom events + console logging for development.
 */

type EventProps = Record<string, string | number | boolean | undefined>

function isProduction(): boolean {
  return process.env.NODE_ENV === 'production'
}

function logEvent(eventName: string, properties?: EventProps): void {
  if (!isProduction()) {
    console.log(`[Analytics] ${eventName}`, properties)
  }
}

/**
 * Track video upload started
 */
export function trackUploadStarted(props: {
  filename: string
  fileSize: number
  fileType: string
}): void {
  logEvent('upload_started', {
    filename: props.filename,
    fileSize: props.fileSize,
    fileType: props.fileType,
  })
}

/**
 * Track upload success (file uploaded to S3)
 */
export function trackUploadSuccess(props: {
  filename: string
  jobId: string
  processingTimeMs: number
}): void {
  logEvent('upload_success', {
    filename: props.filename,
    jobId: props.jobId,
    processingTimeMs: props.processingTimeMs,
  })
}

/**
 * Track watermark processing completed
 */
export function trackWatermarkCompleted(props: {
  jobId: string
  processingTimeMs: number
  outputSize: number
}): void {
  logEvent('watermark_completed', {
    jobId: props.jobId,
    processingTimeMs: props.processingTimeMs,
    outputSize: props.outputSize,
  })
}

/**
 * Track video download started
 */
export function trackDownloadStarted(props: {
  jobId: string
  filename: string
}): void {
  logEvent('download_started', {
    jobId: props.jobId,
    filename: props.filename,
  })
}

/**
 * Track errors
 */
export function trackError(props: {
  errorType: string
  errorMessage: string
  context?: string
}): void {
  logEvent('error', {
    errorType: props.errorType,
    errorMessage: props.errorMessage,
    context: props.context,
  })
}

/**
 * Track user registration/signup
 */
export function trackRegistration(props: {
  method: 'email' | 'wallet'
  timestamp: number
}): void {
  logEvent('registration', {
    method: props.method,
  })
}

/**
 * Track page views (for funnel analysis)
 */
export function trackPageView(props: {
  page: string
  referrer?: string
}): void {
  logEvent('page_view', {
    page: props.page,
    referrer: props.referrer,
  })
}
