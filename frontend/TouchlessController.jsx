import React, { useEffect, useRef, useState, useCallback } from 'react';
import { PointFilter2D, OneEuroFilter } from './oneEuroFilter';
import { getTouchlessUsage, consumeTouchlessGesture } from './touchlessQuota';
import { 
  Hand, 
  Eye, 
  EyeOff, 
  Sparkles, 
  Maximize2, 
  Minimize2, 
  X, 
  HelpCircle,
  AlertCircle,
  Lock,
  Camera,
  RefreshCw,
  Sliders,
  Gauge
} from 'lucide-react';

// MediaPipe Hand Landmark Connections for Skeleton Drawing
const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],       // Thumb
  [0, 5], [5, 6], [6, 7], [7, 8],       // Index
  [5, 9], [9, 10], [10, 11], [11, 12],  // Middle
  [9, 13], [13, 14], [14, 15], [15, 16],// Ring
  [13, 17], [17, 18], [18, 19], [19, 20],// Pinky
  [0, 17]                               // Palm base
];

// Safely stop all tracks on a MediaStream
export const stopStreamTracks = (stream) => {
  if (!stream) return;
  try {
    const tracks = typeof stream.getTracks === 'function' ? stream.getTracks() : [];
    tracks.forEach((track) => {
      try {
        track.stop();
      } catch (_) {}
    });
  } catch (_) {}
};

// Global stop function that cleans up window reference and all video tags across the entire DOM
export const stopAllCameraTracks = () => {
  if (typeof window === 'undefined') return;

  // 1. Stop global window stream
  try {
    if (window.__editodoc_camera_stream) {
      stopStreamTracks(window.__editodoc_camera_stream);
      window.__editodoc_camera_stream = null;
    }
  } catch (_) {}

  // 2. Stop any video element streams across the DOM
  try {
    document.querySelectorAll('video').forEach((vid) => {
      if (vid && vid.srcObject) {
        stopStreamTracks(vid.srcObject);
        vid.srcObject = null;
      }
    });
  } catch (_) {}
};

// Check if a stream has a live, enabled video track
export const isStreamActive = (stream) => {
  if (!stream) return false;
  try {
    const videoTracks = typeof stream.getVideoTracks === 'function' ? stream.getVideoTracks() : [];
    return videoTracks.length > 0 && videoTracks.some((t) => t.readyState === 'live' && t.enabled);
  } catch (_) {
    return false;
  }
};

// Find any existing active stream currently alive in this browser tab
export const findExistingActiveStream = () => {
  if (typeof window !== 'undefined' && isStreamActive(window.__editodoc_camera_stream)) {
    return window.__editodoc_camera_stream;
  }
  if (typeof document !== 'undefined') {
    const vids = document.querySelectorAll('video');
    for (const vid of vids) {
      if (vid && isStreamActive(vid.srcObject)) {
        return vid.srcObject;
      }
    }
  }
  return null;
};

// Detect if a device label is a virtual, phone link, or streaming emulation camera
export const isVirtualOrPhoneCamera = (label = '') => {
  const lower = (label || '').toLowerCase();
  return (
    lower.includes('virtual') ||
    lower.includes('phone') ||
    lower.includes('link') ||
    lower.includes('v2503') ||
    lower.includes('droidcam') ||
    lower.includes('iriun') ||
    lower.includes('epoccam') ||
    lower.includes('camo') ||
    lower.includes('obs')
  );
};

// Detect if a device label is a physical or built-in laptop/desktop webcam
export const isBuiltInWebcam = (label = '') => {
  const lower = (label || '').toLowerCase();
  return (
    lower.includes('wide vision') ||
    lower.includes('integrated') ||
    lower.includes('built-in') ||
    lower.includes('internal') ||
    lower.includes('hp') ||
    lower.includes('hd camera') ||
    lower.includes('webcam') ||
    lower.includes('facetime') ||
    lower.includes('front')
  );
};

// Sort cameras so real physical laptop webcams are prioritized at index 0, virtual phone cameras at bottom
export const sortCamerasByPreference = (devices = []) => {
  return [...devices].sort((a, b) => {
    const aLabel = (a.label || '').toLowerCase();
    const bLabel = (b.label || '').toLowerCase();
    const aVirtual = isVirtualOrPhoneCamera(aLabel);
    const bVirtual = isVirtualOrPhoneCamera(bLabel);
    if (!aVirtual && bVirtual) return -1;
    if (aVirtual && !bVirtual) return 1;
    const aBuiltin = isBuiltInWebcam(aLabel);
    const bBuiltin = isBuiltInWebcam(bLabel);
    if (aBuiltin && !bBuiltin) return -1;
    if (!aBuiltin && bBuiltin) return 1;
    return aLabel.localeCompare(bLabel);
  });
};

// Pick the best physical webcam from currently enumerated devices
export const pickBestCameraId = (devices = []) => {
  const videoInputs = devices.filter((d) => d.kind === 'videoinput');
  if (videoInputs.length === 0) return null;

  // 1. Physical/Built-in webcam (HP Wide Vision, Integrated, etc.)
  const physical = videoInputs.find(
    (d) => d.label && !isVirtualOrPhoneCamera(d.label) && isBuiltInWebcam(d.label)
  );
  if (physical && physical.deviceId) return physical.deviceId;

  // 2. Any non-virtual camera
  const nonVirtual = videoInputs.find(
    (d) => d.label && !isVirtualOrPhoneCamera(d.label)
  );
  if (nonVirtual && nonVirtual.deviceId) return nonVirtual.deviceId;

  // 3. First available
  return videoInputs[0]?.deviceId || null;
};

// Vite HMR Cleanup Hook: Automatically frees hardware camera when file hot-reloads in development
if (typeof import.meta !== 'undefined' && import.meta.hot) {
  import.meta.hot.dispose(() => {
    stopAllCameraTracks();
  });
}

export default function TouchlessController({
  onScroll,
  onNextPage,
  onPrevPage,
  onZoomIn,
  onZoomOut,
  onLaserMove,
  onPinchClick,
  containerRef,
  customStyle = {}
}) {
  // Unlimited gestures for evaluation & new project
  const isPremium = true;

  const [isActive, setIsActive] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Initializing...');
  const [currentGesture, setCurrentGesture] = useState('None');
  const [isMinimized, setIsMinimized] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [quota, setQuota] = useState(() => getTouchlessUsage(isPremium));
  const [laserPos, setLaserPos] = useState(null); // { x, y }
  const [isPinching, setIsPinching] = useState(false);
  const [showQuotaWarning, setShowQuotaWarning] = useState(false);
  const [availableCameras, setAvailableCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [showCameraSelect, setShowCameraSelect] = useState(false);
  const [cameraError, setCameraError] = useState(null);

  // ── Mouse & Scroll Sensitivity / Speed Settings ──
  const [pointerSpeed, setPointerSpeed] = useState(() => {
    const saved = localStorage.getItem('touchless_pointer_speed');
    return saved ? parseFloat(saved) : 1.3;
  });
  const [scrollSpeed, setScrollSpeed] = useState(() => {
    const saved = localStorage.getItem('touchless_scroll_speed');
    return saved ? parseFloat(saved) : 1.0;
  });
  const [invertDirection, setInvertDirection] = useState(() => {
    const saved = localStorage.getItem('touchless_invert_direction');
    return saved !== null ? saved === 'true' : true; // Default true: natural reverted direction
  });
  const [showSettings, setShowSettings] = useState(false);

  const pointerSpeedRef = useRef(pointerSpeed);
  pointerSpeedRef.current = pointerSpeed;

  const scrollSpeedRef = useRef(scrollSpeed);
  scrollSpeedRef.current = scrollSpeed;

  const invertDirectionRef = useRef(invertDirection);
  invertDirectionRef.current = invertDirection;

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const landmarkerRef = useRef(null);
  const animFrameRef = useRef(null);
  const streamRef = useRef(null);

  // Filters & State tracking
  const filterRef = useRef(new PointFilter2D(1.1, 0.009, 1.0));
  const scrollFilterRef = useRef(new OneEuroFilter(0.7, 0.006, 1.0));
  const scrollAnchorYRef = useRef(null); // Reference anchor Y position for Auto-Scroll Joystick
  const scrollGraceFramesRef = useRef(0); // Grace window to prevent dropped detection on downward motion
  const prevScrollYRef = useRef(null);
  const pinchStateRef = useRef(false);
  const lastGestureConsumeRef = useRef(0);
  const lastSwipeTimeRef = useRef(0);
  const lastZoomTimeRef = useRef(0);
  const thumbHoldStartRef = useRef(0);
  const lastDetectedThumbDirRef = useRef(null);
  const historyXRef = useRef([]); // for swipe detection: [{ x, time }]

  // Refresh quota when tier changes
  useEffect(() => {
    setQuota(getTouchlessUsage(isPremium));
  }, [isPremium]);

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('touchless_pointer_speed', pointerSpeed.toString());
  }, [pointerSpeed]);

  useEffect(() => {
    localStorage.setItem('touchless_scroll_speed', scrollSpeed.toString());
  }, [scrollSpeed]);

  useEffect(() => {
    localStorage.setItem('touchless_invert_direction', invertDirection.toString());
  }, [invertDirection]);

  // Callback ref to reliably attach stream whenever the <video> element mounts
  const attachVideoRef = useCallback((node) => {
    videoRef.current = node;
    if (node && streamRef.current) {
      if (node.srcObject !== streamRef.current) {
        node.srcObject = streamRef.current;
      }
      node.play().catch((err) => console.warn('Video play error on attach:', err));
    }
  }, []);

  // Ensure stream stays bound whenever isActive or camera changes
  useEffect(() => {
    if (isActive && videoRef.current && streamRef.current) {
      if (videoRef.current.srcObject !== streamRef.current) {
        videoRef.current.srcObject = streamRef.current;
      }
      videoRef.current.play().catch((err) => console.warn('Video play error in effect:', err));
    }
  }, [isActive, selectedCameraId]);

  // Record a gesture event toward daily quota
  const recordGesture = useCallback((gestureType) => {
    const now = performance.now();
    // Debounce quota consumption to prevent consuming all 100 in 1 second of continuous scrolling
    if (now - lastGestureConsumeRef.current > 500) {
      lastGestureConsumeRef.current = now;
      const res = consumeTouchlessGesture(isPremium);
      setQuota(getTouchlessUsage(isPremium));
      if (!res.allowed) {
        setShowQuotaWarning(true);
        return false;
      }
    }
    return true;
  }, [isPremium]);

  // 1. Initialize MediaPipe HandLandmarker via WebAssembly (Client-side only)
  const initHandLandmarker = async () => {
    if (landmarkerRef.current) return landmarkerRef.current;
    setStatusMessage('Loading AI Hand Tracker (WASM)...');

    const { HandLandmarker, FilesetResolver } = await import('@mediapipe/tasks-vision');
    const vision = await FilesetResolver.forVisionTasks(
      'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm'
    );

    try {
      const landmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath:
            'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task',
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
        numHands: 1,
      });

      landmarkerRef.current = landmarker;
      return landmarker;
    } catch (gpuErr) {
      console.warn('MediaPipe GPU initialization failed, falling back to CPU:', gpuErr);
      const landmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath:
            'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task',
          delegate: 'CPU',
        },
        runningMode: 'VIDEO',
        numHands: 1,
      });

      landmarkerRef.current = landmarker;
      return landmarker;
    }
  };

  const startCameraStream = async (targetDeviceId = null, forceNew = false) => {
    // 1. If an active stream is already playing with live tracks in this tab, reuse it
    if (!forceNew && streamRef.current && isStreamActive(streamRef.current)) {
      const activeTrack = streamRef.current.getVideoTracks()[0];
      const activeId = activeTrack?.getSettings?.()?.deviceId;
      if (!targetDeviceId || activeId === targetDeviceId) {
        setCameraError(null);
        return streamRef.current;
      }
    }

    // 2. Stop any existing tracks and wait briefly for driver release
    stopAllCameraTracks();
    if (streamRef.current) {
      stopStreamTracks(streamRef.current);
      streamRef.current = null;
    }

    await new Promise((r) => setTimeout(r, 200));

    // Determine target device
    let selectedId = targetDeviceId;
    if (!selectedId) {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        selectedId = pickBestCameraId(devices);
      } catch (_) {}
    }

    // Helper to safely get stream
    const tryGetStream = async (constraints) => {
      return await navigator.mediaDevices.getUserMedia({
        video: constraints,
        audio: false,
      });
    };

    let stream = null;

    // Attempt 1: Target the specific physical camera if known
    if (selectedId) {
      try {
        stream = await tryGetStream({
          deviceId: { exact: selectedId },
          width: { ideal: 640 },
          height: { ideal: 480 },
        });
      } catch (err1) {
        console.warn('Targeted camera exact deviceId failed, attempting ideal:', err1);
        try {
          stream = await tryGetStream({
            deviceId: { ideal: selectedId },
            width: { ideal: 640 },
            height: { ideal: 480 },
          });
        } catch (err2) {
          console.warn('Targeted camera ideal deviceId failed:', err2);
        }
      }
    }

    // Attempt 2: If targeted failed or no target was specified, try standard resolution
    if (!stream) {
      try {
        stream = await tryGetStream({
          width: { ideal: 640 },
          height: { ideal: 480 },
        });
      } catch (err3) {
        console.warn('Standard constraints failed, trying basic video: true:', err3);
        // Attempt 3: Absolute simplest generic video constraint
        stream = await tryGetStream(true);
      }
    }

    streamRef.current = stream;
    if (typeof window !== 'undefined') {
      window.__editodoc_camera_stream = stream;
    }

    // Refresh devices list
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices.filter((d) => d.kind === 'videoinput');
      const sorted = sortCamerasByPreference(videoInputs);
      setAvailableCameras(sorted);

      const activeTrack = stream.getVideoTracks()[0];
      const activeId = activeTrack?.getSettings?.()?.deviceId;
      const activeLabel = activeTrack?.label || '';

      // If Chrome grabbed virtual phone camera, but physical webcam is available:
      if (!targetDeviceId && isVirtualOrPhoneCamera(activeLabel) && sorted.length > 0 && !isVirtualOrPhoneCamera(sorted[0].label)) {
        console.log('Virtual phone camera was opened; auto-switching to physical webcam:', sorted[0].label);
        const physicalCam = sorted[0];
        setSelectedCameraId(physicalCam.deviceId);
        return await startCameraStream(physicalCam.deviceId, true);
      }

      if (activeId) {
        setSelectedCameraId(activeId);
      }
    } catch (_) {}

    // Attach stream to video element and wait for metadata
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      try {
        await new Promise((resolve) => {
          if (videoRef.current.readyState >= 2) {
            videoRef.current.play().catch(() => {});
            resolve();
          } else {
            videoRef.current.onloadedmetadata = () => {
              videoRef.current.play().catch(() => {});
              resolve();
            };
            setTimeout(resolve, 300);
          }
        });
      } catch (_) {}
    }

    setCameraError(null);
    return stream;
  };

  const handleForceResetCamera = async () => {
    try {
      setIsInitializing(true);
      setStatusMessage('Resetting webcam hardware...');
      stopAllCameraTracks();
      if (streamRef.current) {
        stopStreamTracks(streamRef.current);
        streamRef.current = null;
      }
      await new Promise((r) => setTimeout(r, 400));
      await initHandLandmarker();
      await startCameraStream(null, true);
      setIsActive(true);
      setIsInitializing(false);
      setStatusMessage('Touchless Active 🖐️');
      setCameraError(null);
    } catch (err) {
      console.error('Force camera reset failed:', err);
      setIsInitializing(false);
      setIsActive(false);
      setCameraError({
        title: 'Webcam Hardware In Use',
        message: 'Your webcam is still locked by another tab or program (e.g. Windows Camera, Zoom, Teams, or another open browser window). Please close other camera apps and click "Force Reset & Connect" again.',
        canRetry: true,
        forceReset: true,
      });
    }
  };

  const switchCamera = async (deviceId) => {
    try {
      setSelectedCameraId(deviceId);
      setStatusMessage('Connecting Camera...');
      const stream = await startCameraStream(deviceId, true);
      if (videoRef.current && stream) {
        videoRef.current.srcObject = stream;
        try {
          await videoRef.current.play();
        } catch (_) {}
      }
      setStatusMessage('Touchless Active 🖐️');
    } catch (err) {
      console.error('Error switching camera:', err);
      const camObj = availableCameras.find((c) => c.deviceId === deviceId);
      const camName = camObj ? camObj.label : 'Selected Camera';
      setCameraError({
        title: `${camName} Locked / In Use`,
        message: `${camName} is currently locked by another window, profile, or app (such as your other open Chrome window or tab). Please stop Touchless Mode in that window first, then click "Force Reset & Connect".`,
        canRetry: true,
        forceReset: true,
      });
    }
  };

  // 2. Start / Stop Touchless Camera
  const toggleTouchless = async () => {
    if (isActive) {
      // Stop Camera
      stopAllCameraTracks();
      if (streamRef.current) {
        stopStreamTracks(streamRef.current);
        streamRef.current = null;
      }
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
      filterRef.current.reset();
      scrollFilterRef.current.reset();
      setIsActive(false);
      setLaserPos(null);
      setCurrentGesture('Off');
      setCameraError(null);
      return;
    }

    // Check if free user is already out of quota
    const currentUsage = getTouchlessUsage(isPremium);
    if (currentUsage.exhausted) {
      setShowQuotaWarning(true);
      return;
    }

    try {
      setCameraError(null);
      setIsInitializing(true);
      setStatusMessage('Loading AI Hand Tracker...');
      await initHandLandmarker();

      setStatusMessage('Connecting Camera...');
      await startCameraStream(selectedCameraId || null);

      setIsActive(true);
      setIsInitializing(false);
      setStatusMessage('Touchless Active 🖐️');
    } catch (err) {
      console.error('Touchless initialization error:', err);
      setIsInitializing(false);
      setIsActive(false);

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraError({
          title: 'Camera Access Blocked',
          message: 'Camera permission is blocked in your browser. Click the lock/sliders icon 🎚️ next to localhost:5173 in the URL bar, set Camera to "Allow", and reload.',
          canRetry: true,
          forceReset: false,
        });
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraError({
          title: 'Webcam In Use / Locked',
          message: 'Your webcam is held by another tab or program (Zoom, Teams, or another window). Click "Force Reset & Connect" below to clear any stuck hardware handles.',
          canRetry: true,
          forceReset: true,
        });
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraError({
          title: 'No Webcam Found',
          message: 'No camera found on your device. Please ensure your webcam is connected or enabled in Windows Settings.',
          canRetry: false,
          forceReset: false,
        });
      } else {
        setCameraError({
          title: 'Camera Connection Failed',
          message: err.message || 'Unable to open video stream.',
          canRetry: true,
          forceReset: true,
        });
      }
    }
  };

  // Cleanup on unmount or tab close
  useEffect(() => {
    const handleBeforeUnload = () => {
      stopAllCameraTracks();
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      stopAllCameraTracks();
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  // 3. Main Gesture Detection & Vision Loop
  useEffect(() => {
    if (!isActive) return;

    let lastVideoTime = -1;

    const processFrame = () => {
      if (
        videoRef.current &&
        videoRef.current.readyState >= 2 &&
        landmarkerRef.current &&
        canvasRef.current
      ) {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const now = performance.now();

        if (video.currentTime !== lastVideoTime) {
          lastVideoTime = video.currentTime;
          const detections = landmarkerRef.current.detectForVideo(video, now);

          ctx.clearRect(0, 0, canvas.width, canvas.height);

          if (detections.landmarks && detections.landmarks.length > 0) {
            const lms = detections.landmarks[0];

            // Draw Hand Skeleton
            drawHandSkeleton(ctx, lms, canvas.width, canvas.height);

            // Key Landmarks
            const wrist = lms[0];
            const thumbTip = lms[4];
            const indexMcp = lms[5];
            const indexPip = lms[6];
            const indexTip = lms[8];
            const middleMcp = lms[9];
            const middlePip = lms[10];
            const middleTip = lms[12];
            const ringMcp = lms[13];
            const ringPip = lms[14];
            const ringTip = lms[16];
            const pinkyMcp = lms[17];
            const pinkyPip = lms[18];
            const pinkyTip = lms[20];

            // Key Landmark References
            const thumbPip = lms[2]; // MCP
            const thumbIp = lms[3];

            // 2D Euclidean distance helper
            const dist = (p1, p2) => Math.hypot(p1.x - p2.x, p1.y - p2.y);

            // Robust Extension & Curl calculation:
            // Checks both Y coordinate AND distance-to-wrist / distance-to-knuckle (MCP)
            // Stays reliably detected even when hand moves DOWN towards bottom of camera or tilts forward
            const isIndexExtended =
              indexTip.y < indexPip.y ||
              (dist(indexTip, wrist) > dist(indexPip, wrist) * 1.05 && dist(indexTip, indexMcp) > dist(indexPip, indexMcp) * 1.15);
            const isIndexCurled =
              indexTip.y > indexPip.y ||
              dist(indexTip, indexMcp) < 0.14 ||
              dist(indexTip, wrist) < dist(indexPip, wrist) * 1.02;

            const isMiddleExtended =
              middleTip.y < middlePip.y ||
              (dist(middleTip, wrist) > dist(middlePip, wrist) * 1.05 && dist(middleTip, middleMcp) > dist(middlePip, middleMcp) * 1.15);
            const isMiddleCurled =
              middleTip.y > middlePip.y ||
              dist(middleTip, middleMcp) < 0.14 ||
              dist(middleTip, wrist) < dist(middlePip, wrist) * 1.02;

            const isRingExtended =
              ringTip.y < ringPip.y &&
              dist(ringTip, ringMcp) > dist(ringPip, ringMcp) * 1.2;
            const isRingCurled =
              ringTip.y > ringPip.y ||
              dist(ringTip, ringMcp) < dist(ringPip, ringMcp) * 1.15 ||
              dist(ringTip, wrist) < dist(ringPip, wrist) * 1.06;

            const isPinkyExtended =
              pinkyTip.y < pinkyPip.y &&
              dist(pinkyTip, pinkyMcp) > dist(pinkyPip, pinkyMcp) * 1.2;
            const isPinkyCurled =
              pinkyTip.y > pinkyPip.y ||
              dist(pinkyTip, pinkyMcp) < dist(pinkyPip, pinkyMcp) * 1.15 ||
              dist(pinkyTip, wrist) < dist(pinkyPip, wrist) * 1.06;

            // Stable palm center calculation in mirrored coordinates
            const palmCenterX = 1.0 - (wrist.x + lms[9].x) / 2;

            // Mirror X for intuitive natural mirror interaction
            const rawMirroredX = 1.0 - indexTip.x;
            const smoothed = filterRef.current.filter(rawMirroredX, indexTip.y, now / 1000);

            // ── Real Mouse Pointer Speed & Dynamic Ballistics (Range 0.5x to 2.5x) ──
            const pSpeed = pointerSpeedRef.current;
            const neutralCenterX = 0.5;
            const neutralCenterY = 0.45; // slightly above vertical center where hands naturally rest

            const rawDeltaX = (smoothed.x - neutralCenterX) * pSpeed;
            const rawDeltaY = (smoothed.y - neutralCenterY) * pSpeed;

            // Ballistics: Gentle precision for small movements, acceleration boost for fast sweeps
            const distFromCenter = Math.hypot(rawDeltaX, rawDeltaY);
            const accel = 1.0 + (distFromCenter > 0.12 ? Math.min(0.75, (distFromCenter - 0.12) * 1.3) : 0);

            const mappedX = neutralCenterX + rawDeltaX * accel;
            const mappedY = neutralCenterY + rawDeltaY * accel;

            // Clamp safely within visible screen boundaries
            const clampedX = Math.max(0.005, Math.min(0.995, mappedX));
            const clampedY = Math.max(0.005, Math.min(0.995, mappedY));

            const screenX = clampedX * window.innerWidth;
            const screenY = clampedY * window.innerHeight;

            // ── 1. HORIZONTAL SWIPE (2 or 3 Fingers Flick Left/Right; 1-Finger Completely Excluded) ──
            const isThreeFingers = isIndexExtended && isMiddleExtended && isRingExtended && isPinkyCurled;
            const isTwoFingers = isIndexExtended && isMiddleExtended && isRingCurled && isPinkyCurled;

            const rawCentroidY = (indexTip.y + middleTip.y) / 2;
            historyXRef.current.push({ x: palmCenterX, y: rawCentroidY, time: now });
            if (historyXRef.current.length > 10) historyXRef.current.shift();

            let isSwiping = false;
            let swipeDirection = null;
            let swipeGestureType = null;

            if (historyXRef.current.length >= 3) {
              const oldest = historyXRef.current[0];
              const newest = historyXRef.current[historyXRef.current.length - 1];
              const dt = (newest.time - oldest.time) / 1000;
              const dx = newest.x - oldest.x;
              const dy = (newest.y || 0) - (oldest.y || 0);

              if (dt >= 0.04 && dt <= 0.40) {
                const velocityX = dx / dt; // screen width per second

                // Invert swipe direction as requested:
                // Flick Left (< 0) ➔ Next Page
                // Flick Right (> 0) ➔ Prev Page
                const isInverted = invertDirectionRef.current;
                const nextDir = isInverted ? 'next' : 'prev';
                const prevDir = isInverted ? 'prev' : 'next';

                // ONLY 2-finger or 3-finger hand shapes can trigger a horizontal swipe
                // Single finger (laser pointer) is 100% EXCLUDED from swiping
                if (isThreeFingers) {
                  // 3 fingers: effortless horizontal flick
                  if (Math.abs(dx) > Math.abs(dy) * 1.1) {
                    if (velocityX < -0.24) {
                      isSwiping = true;
                      swipeDirection = nextDir;
                      swipeGestureType = '3-finger';
                    } else if (velocityX > 0.24) {
                      isSwiping = true;
                      swipeDirection = prevDir;
                      swipeGestureType = '3-finger';
                    }
                  }
                } else if (isTwoFingers) {
                  // 2 fingers: deliberate horizontal flick (must be predominantly horizontal)
                  if (Math.abs(dx) > Math.abs(dy) * 1.35 && Math.abs(dx) > 0.08) {
                    if (velocityX < -0.36) {
                      isSwiping = true;
                      swipeDirection = nextDir;
                      swipeGestureType = '2-finger';
                    } else if (velocityX > 0.36) {
                      isSwiping = true;
                      swipeDirection = prevDir;
                      swipeGestureType = '2-finger';
                    }
                  }
                }
              }
            }

            if (isSwiping && now - lastSwipeTimeRef.current > 550) {
              lastSwipeTimeRef.current = now;
              historyXRef.current = []; // Reset history
              scrollAnchorYRef.current = null;
              scrollGraceFramesRef.current = 0;
              prevScrollYRef.current = null;
              scrollFilterRef.current.reset();
              setLaserPos(null);

              if (swipeDirection === 'next') {
                setCurrentGesture(swipeGestureType === '3-finger' ? '🤟 3-Finger Next ➔' : '✌️ 2-Finger Next ➔');
                if (recordGesture('swipe_next')) {
                  if (onNextPage) onNextPage();
                  window.dispatchEvent(new CustomEvent('editodoc:nextPage'));
                }
              } else if (swipeDirection === 'prev') {
                setCurrentGesture(swipeGestureType === '3-finger' ? '⬅ 🤟 3-Finger Prev' : '⬅ ✌️ 2-Finger Prev');
                if (recordGesture('swipe_prev')) {
                  if (onPrevPage) onPrevPage();
                  window.dispatchEvent(new CustomEvent('editodoc:prevPage'));
                }
              }
            } else if (isThreeFingers && !isSwiping) {
              // 3 fingers extended and ready for horizontal flick
              setCurrentGesture('🤟 3 Fingers (Flick Left ➔ / Right ⬅)');
              scrollAnchorYRef.current = null;
              scrollGraceFramesRef.current = 0;
              prevScrollYRef.current = null;
              scrollFilterRef.current.reset();
              setLaserPos(null);
            }
            // ── 2. STATIC GESTURES ──
            else {
              // Pinch contact distance between thumb tip and index tip
              const pinchDist = Math.hypot(indexTip.x - thumbTip.x, indexTip.y - thumbTip.y);
              // Hysteresis: enter pinch at < 0.062, stay pinched until > 0.082
              const isPinchContact = pinchDist < 0.062 || (pinchStateRef.current && pinchDist < 0.082);

              const allFourCurled = isIndexCurled && isMiddleCurled && isRingCurled && isPinkyCurled;
              const thumbDistFromPalm = Math.hypot(thumbTip.x - lms[9].x, thumbTip.y - lms[9].y);
              const thumbLengthFromMcp = Math.hypot(thumbTip.x - lms[2].x, thumbTip.y - lms[2].y);

              // Genuine deliberate Thumbs Up: Thumb pointing straight UP, well clear of knuckles, extended
              const isRealThumbUp =
                allFourCurled &&
                thumbTip.y < thumbIp.y - 0.05 &&
                thumbTip.y < thumbPip.y - 0.07 &&
                thumbTip.y < lms[5].y - 0.06 &&
                thumbDistFromPalm > 0.15 &&
                thumbLengthFromMcp > 0.09;

              // Genuine deliberate Thumbs Down: Thumb pointing straight DOWN, well clear of knuckles
              const isRealThumbDown =
                allFourCurled &&
                thumbTip.y > thumbIp.y + 0.05 &&
                thumbTip.y > thumbPip.y + 0.07 &&
                thumbTip.y > lms[0].y + 0.04 &&
                thumbDistFromPalm > 0.15 &&
                thumbLengthFromMcp > 0.09;

              // Laser Pointer / Pinch Click mode:
              // User is pointing with index finger OR actively pinching index + thumb to click.
              // Remaining fingers (middle, ring, pinky) are curled.
              const isPointerOrPinch = (isIndexExtended || isPinchContact) && isMiddleCurled && isRingCurled && isPinkyCurled;

              // Genuine deliberate Closed Fist / Grab Hand:
              // All 4 fingers curled into palm, thumb tucked/neutral, NOT pinching index to thumb!
              // In a true fist, index tip is tucked inside palm, so pinchDist is > 0.075
              const isClosedFist = allFourCurled && !isRealThumbUp && !isRealThumbDown && !isPinchContact && pinchDist > 0.075;

              // Two-finger scroll and distinct gesture identifiers
              const isTwoFingers = isIndexExtended && isMiddleExtended && isRingCurled && isPinkyCurled;
              const isPalm = isIndexExtended && isMiddleExtended && isRingExtended && isPinkyExtended;

              // Grace window: if user was already scrolling, allow a small grace period (up to 8 frames / ~130ms)
              // to prevent momentary drops when the hand dips down or fingers tilt towards the camera
              const shouldContinueScroll =
                isTwoFingers ||
                (scrollAnchorYRef.current !== null &&
                  scrollGraceFramesRef.current > 0 &&
                  !isClosedFist &&
                  !isPointerOrPinch &&
                  !isPalm);

              // --- GESTURE A: THUMBS UP 👍 (ZOOM IN with 300ms hold requirement) ---
              if (isRealThumbUp) {
                if (lastDetectedThumbDirRef.current !== 'up') {
                  lastDetectedThumbDirRef.current = 'up';
                  thumbHoldStartRef.current = now;
                }
                const holdDuration = now - thumbHoldStartRef.current;
                if (holdDuration < 300) {
                  setCurrentGesture('👍 Hold Thumbs Up to Zoom In...');
                } else {
                  setCurrentGesture('👍 Zoom In (+15%)');
                  if (now - lastZoomTimeRef.current > 500) {
                    lastZoomTimeRef.current = now;
                    if (recordGesture('zoom_in')) {
                      if (onZoomIn) onZoomIn();
                      window.dispatchEvent(new CustomEvent('editodoc:zoomIn'));
                    }
                  }
                }
                scrollAnchorYRef.current = null;
                scrollGraceFramesRef.current = 0;
                prevScrollYRef.current = null;
                setLaserPos(null);
              }
              // --- GESTURE B: THUMBS DOWN 👎 (ZOOM OUT with 300ms hold requirement) ---
              else if (isRealThumbDown) {
                if (lastDetectedThumbDirRef.current !== 'down') {
                  lastDetectedThumbDirRef.current = 'down';
                  thumbHoldStartRef.current = now;
                }
                const holdDuration = now - thumbHoldStartRef.current;
                if (holdDuration < 300) {
                  setCurrentGesture('👎 Hold Thumbs Down to Zoom Out...');
                } else {
                  setCurrentGesture('👎 Zoom Out (-15%)');
                  if (now - lastZoomTimeRef.current > 500) {
                    lastZoomTimeRef.current = now;
                    if (recordGesture('zoom_out')) {
                      if (onZoomOut) onZoomOut();
                      window.dispatchEvent(new CustomEvent('editodoc:zoomOut'));
                    }
                  }
                }
                scrollAnchorYRef.current = null;
                scrollGraceFramesRef.current = 0;
                prevScrollYRef.current = null;
                setLaserPos(null);
              }
              // --- GESTURE C: INDEX POINTING 👆 / PINCH CLICK 👌 (PRIORITIZED OVER FIST) ---
              else if (isPointerOrPinch) {
                scrollAnchorYRef.current = null;
                scrollGraceFramesRef.current = 0;
                prevScrollYRef.current = null;
                scrollFilterRef.current.reset();

                // During a click, freeze laser coordinates so the click stays solidly on target
                if (!pinchStateRef.current) {
                  setLaserPos({ x: screenX, y: screenY });
                  if (onLaserMove) onLaserMove({ x: screenX, y: screenY });
                }

                if (isPinchContact) {
                  if (!pinchStateRef.current) {
                    pinchStateRef.current = true;
                    setIsPinching(true);
                    setCurrentGesture('👌 Pinch (Click)');

                    if (recordGesture('pinch')) {
                      const targetEl = document.elementFromPoint(screenX, screenY);
                      if (targetEl) {
                        targetEl.click();
                      }
                      if (onPinchClick) onPinchClick({ x: screenX, y: screenY });
                      window.dispatchEvent(
                        new CustomEvent('editodoc:pinchClick', { detail: { x: screenX, y: screenY } })
                      );
                    }
                  } else {
                    setCurrentGesture('👌 Pinch (Click)');
                  }
                } else {
                  if (pinchStateRef.current) {
                    pinchStateRef.current = false;
                    setIsPinching(false);
                  }
                  setCurrentGesture('👆 Laser Pointer');
                }
              }
              // --- GESTURE D: CLOSED FIST / GRAB HAND ✊ (IMMEDIATELY STOP & LOCK POSITION) ---
              else if (isClosedFist) {
                thumbHoldStartRef.current = 0;
                lastDetectedThumbDirRef.current = null;
                scrollAnchorYRef.current = null;
                scrollGraceFramesRef.current = 0;
                prevScrollYRef.current = null;
                scrollFilterRef.current.reset();
                setLaserPos(null);
                setCurrentGesture('✊ Hand Closed (Locked)');
              }
              // --- GESTURE E: TWO FINGERS ✌️ (AUTO-SCROLL JOYSTICK WITH SPEED & STOP CONTROL) ---
              else if (shouldContinueScroll) {
                if (isTwoFingers) {
                  scrollGraceFramesRef.current = 8; // Refresh grace frames
                } else {
                  scrollGraceFramesRef.current -= 1; // Decrement during momentary drop
                }

                thumbHoldStartRef.current = 0;
                lastDetectedThumbDirRef.current = null;
                setLaserPos(null);

                // Track geometric centroid of 2 fingers (tips + PIP joints)
                // Pitch-invariant: stays completely stable even when fingers tilt forward or downward
                const rawY = (indexTip.y + middleTip.y + indexPip.y + middlePip.y) / 4;
                const smoothedY = scrollFilterRef.current.filter(rawY, now / 1000);

                // 1. Initial lock-in: user showed 2 fingers, ready for scrolling!
                if (scrollAnchorYRef.current === null) {
                  scrollAnchorYRef.current = smoothedY;
                  setCurrentGesture('✌️ 2-Fingers Ready (Move Up / Down)');
                } else {
                  // 2. Measure vertical distance from established anchor
                  // Note: in camera coords (y=0 top, y=1 bottom):
                  // diffFromAnchor < 0 means user moved hand UP
                  // diffFromAnchor > 0 means user moved hand DOWN
                  const diffFromAnchor = smoothedY - scrollAnchorYRef.current;
                  const absDiff = Math.abs(diffFromAnchor);

                  // Deadzone: ~2.8% of camera height (ignores hand micro-tremor when holding still)
                  const deadzone = 0.028;

                  if (absDiff <= deadzone) {
                    setCurrentGesture('✌️ 2-Fingers Ready (Centered)');
                  } else {
                    const offset = absDiff - deadzone;
                    const isHandUp = diffFromAnchor < 0;

                    // Progressive auto-scroll speed tiers:
                    // Slow: slight tilt (< 0.055 offset) -> 3.0 to 6.8 px/frame (steady readable scroll)
                    // Normal: moderate tilt (0.055 - 0.13 offset) -> 6.8 to 17.5 px/frame
                    // Fast 🚀: higher tilt (> 0.13 offset) -> 17.5 to 45 px/frame
                    let baseSpeed;
                    let speedLabel;
                    if (offset < 0.055) {
                      baseSpeed = 3.0 + offset * 70;
                      speedLabel = 'Slow';
                    } else if (offset < 0.13) {
                      baseSpeed = 6.8 + (offset - 0.055) * 140;
                      speedLabel = 'Normal';
                    } else {
                      baseSpeed = 17.5 + Math.min(30, (offset - 0.13) * 220);
                      speedLabel = 'Fast 🚀';
                    }

                    // Direction mapping:
                    // Standard:
                    //   Hand Up (diff < 0) -> deltaY < 0 (scroll UP towards document top)
                    //   Hand Down (diff > 0) -> deltaY > 0 (scroll DOWN towards document bottom)
                    // Inverted:
                    //   Hand Up -> deltaY > 0 (scroll DOWN)
                    //   Hand Down -> deltaY < 0 (scroll UP)
                    const scrollSign = invertDirectionRef.current ? -1 : 1;
                    const directionSign = (isHandUp ? -1 : 1) * scrollSign;
                    const sSpeed = scrollSpeedRef.current;
                    const deltaY = directionSign * baseSpeed * sSpeed;

                    const isScrollingUp = deltaY < 0;
                    const dirBadge = isScrollingUp ? '▲ Up' : '▼ Down';
                    setCurrentGesture(`✌️ Auto-Scroll ${dirBadge} (${speedLabel})`);

                    if (recordGesture('scroll')) {
                      let handledDirectly = false;
                      if (onScroll) {
                        onScroll(deltaY);
                        handledDirectly = true;
                      } else if (containerRef && containerRef.current) {
                        containerRef.current.scrollTop += deltaY;
                        handledDirectly = true;
                      } else {
                        const scrollEl = document.querySelector('[data-touchless-scroll="true"]');
                        if (scrollEl) {
                          scrollEl.scrollTop += deltaY;
                          handledDirectly = true;
                        }
                      }

                      // Dispatch event with directHandled flag to prevent double-scrolling glitch
                      window.dispatchEvent(
                        new CustomEvent('editodoc:scroll', { detail: { deltaY, directHandled: handledDirectly } })
                      );

                      if (!handledDirectly) {
                        window.scrollBy({ top: deltaY, behavior: 'auto' });
                      }
                    }
                  }
                }
              }
              // --- GESTURE F: OPEN PALM 🖐️ (STANDBY / PAUSE) ---
              else if (isPalm) {
                setCurrentGesture('🖐️ Palm (Ready)');
                scrollAnchorYRef.current = null;
                scrollGraceFramesRef.current = 0;
                prevScrollYRef.current = null;
                scrollFilterRef.current.reset();
                setLaserPos(null);
              } else {
                scrollAnchorYRef.current = null;
                scrollGraceFramesRef.current = 0;
                prevScrollYRef.current = null;
                scrollFilterRef.current.reset();
                setLaserPos(null);
                setCurrentGesture('Tracking hand...');
              }
            }
          } else {
            setCurrentGesture('Searching hand...');
            if (scrollGraceFramesRef.current > 0) {
              scrollGraceFramesRef.current -= 1;
            } else {
              scrollAnchorYRef.current = null;
            }
            prevScrollYRef.current = null;
            scrollFilterRef.current.reset();
            setLaserPos(null);
          }
        }
      }
      animFrameRef.current = requestAnimationFrame(processFrame);
    };

    animFrameRef.current = requestAnimationFrame(processFrame);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isActive, onScroll, onNextPage, onPrevPage, onZoomIn, onZoomOut, onLaserMove, onPinchClick, containerRef, recordGesture]);

  // Helper: Draw Hand Skeleton Landmarks
  const drawHandSkeleton = (ctx, lms, w, h) => {
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#00FFCC';

    // Draw lines
    HAND_CONNECTIONS.forEach(([start, end]) => {
      const p1 = lms[start];
      const p2 = lms[end];
      ctx.beginPath();
      ctx.moveTo((1.0 - p1.x) * w, p1.y * h);
      ctx.lineTo((1.0 - p2.x) * w, p2.y * h);
      ctx.stroke();
    });

    // Draw landmark joints
    lms.forEach((p, idx) => {
      ctx.beginPath();
      ctx.arc((1.0 - p.x) * w, p.y * h, idx === 8 ? 4 : 2.5, 0, 2 * Math.PI);
      ctx.fillStyle = idx === 8 ? '#FF0055' : idx === 4 ? '#FFD700' : '#00FFCC';
      ctx.fill();
    });

    // Visual Joystick Anchor & Deadzone Overlay for Auto-Scroll
    if (scrollAnchorYRef.current !== null) {
      const anchorY = scrollAnchorYRef.current * h;
      const deadzonePx = 0.028 * h;

      // Draw deadzone neutral resting band
      ctx.fillStyle = 'rgba(16, 185, 129, 0.15)';
      ctx.fillRect(0, anchorY - deadzonePx, w, deadzonePx * 2);

      // Draw anchor dashed line
      ctx.save();
      ctx.strokeStyle = '#10B981';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, anchorY);
      ctx.lineTo(w, anchorY);
      ctx.stroke();
      ctx.restore();

      // Anchor badge text
      ctx.fillStyle = '#10B981';
      ctx.font = 'bold 9px Inter, sans-serif';
      ctx.fillText('⚓ Anchor (Resting Line)', 6, Math.max(12, anchorY - 4));
    }
  };

  return (
    <>
      {/* 1. Laser Pointer Dot Overlay */}
      {isActive && laserPos && (
        <div
          style={{
            position: 'fixed',
            left: laserPos.x - 12,
            top: laserPos.y - 12,
            width: 24,
            height: 24,
            borderRadius: '50%',
            pointerEvents: 'none',
            zIndex: 999999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transform: isPinching ? 'scale(1.4)' : 'scale(1)',
            transition: 'transform 0.1s ease',
          }}
        >
          {/* Inner core */}
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: isPinching ? '#00FF88' : '#FF0055',
              boxShadow: isPinching
                ? '0 0 16px #00FF88, 0 0 32px #00FF88'
                : '0 0 16px #FF0055, 0 0 32px #FF0055',
            }}
          />
          {/* Outer glowing pulsing ring */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: '50%',
              border: `2px solid ${isPinching ? 'rgba(0,255,136,0.6)' : 'rgba(255,0,85,0.6)'}`,
              animation: 'pulse 1.2s infinite ease-in-out',
            }}
          />
        </div>
      )}

      {/* Camera Lock / Busy Error Banner */}
      {cameraError && (
        <div
          style={{
            position: 'fixed',
            bottom: '76px',
            right: '24px',
            maxWidth: '380px',
            background: 'rgba(15, 23, 42, 0.98)',
            border: '1px solid rgba(239, 68, 68, 0.45)',
            borderRadius: '14px',
            padding: '14px 16px',
            boxShadow: '0 16px 40px rgba(0, 0, 0, 0.6), 0 0 16px rgba(239, 68, 68, 0.25)',
            zIndex: 99998,
            backdropFilter: 'blur(16px)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
            <AlertCircle size={20} color="#EF4444" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '4px' }}>
                {cameraError.title || 'Webcam In Use / Locked'}
              </div>
              <p style={{ fontSize: '0.74rem', color: '#CBD5E1', margin: '0 0 10px 0', lineHeight: 1.45 }}>
                {cameraError.message}
              </p>
              <div style={{ display: 'flex', gap: '8px' }}>
                {cameraError.canRetry && (
                  <button
                    onClick={() => {
                      if (cameraError.forceReset) {
                        handleForceResetCamera();
                      } else {
                        toggleTouchless();
                      }
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '6px 12px',
                      borderRadius: '8px',
                      background: 'linear-gradient(135deg, #10B981, #059669)',
                      color: '#FFF',
                      border: 'none',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    <RefreshCw size={12} /> Force Reset & Connect
                  </button>
                )}
                <button
                  onClick={() => setCameraError(null)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    color: '#94A3B8',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    fontSize: '0.74rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. Floating Toggle Button (Always Available or in Document Bar) */}
      <div
        className="touchless-floating-toggle"
        style={{
          position: 'fixed',
          bottom: '24px',
          right: isActive ? (isMinimized ? '24px' : '210px') : '24px',
          zIndex: 99990,
          transition: 'right 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          ...customStyle,
        }}
      >
        <button
          onClick={toggleTouchless}
          disabled={isInitializing}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            borderRadius: '24px',
            background: isActive
              ? 'linear-gradient(135deg, #10B981, #059669)'
              : 'linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95))',
            color: '#FFFFFF',
            border: `1px solid ${isActive ? '#34D399' : 'rgba(255, 255, 255, 0.15)'}`,
            boxShadow: isActive
              ? '0 8px 24px rgba(16, 185, 129, 0.35)'
              : '0 8px 24px rgba(0, 0, 0, 0.25)',
            cursor: 'pointer',
            fontSize: '0.85rem',
            fontWeight: 600,
            backdropFilter: 'blur(12px)',
            transition: 'all 0.2s ease',
          }}
          title="Toggle Touchless Hand Gesture Mode"
        >
          <Hand size={16} />
          <span>
            {isInitializing ? 'Starting AI...' : isActive ? 'Touchless: ON' : 'Touchless Mode'}
          </span>
          {isPremium ? (
            <span
              style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '2px 6px',
                borderRadius: '10px',
                fontSize: '0.7rem',
              }}
            >
              PRO
            </span>
          ) : (
            <span
              style={{
                background: quota.remaining < 20 ? 'rgba(239, 68, 68, 0.4)' : 'rgba(255,255,255,0.15)',
                padding: '2px 6px',
                borderRadius: '10px',
                fontSize: '0.7rem',
              }}
            >
              {quota.remaining}/100
            </span>
          )}
        </button>
      </div>

      {/* 3. Compact Picture-in-Picture Box */}
      {isActive && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            width: isMinimized ? '180px' : showSettings ? '230px' : '195px',
            borderRadius: '14px',
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            boxShadow: '0 12px 36px rgba(0,0,0,0.4)',
            overflow: 'hidden',
            zIndex: 99995,
            backdropFilter: 'blur(16px)',
            transition: 'all 0.25s ease',
          }}
        >
          {/* Header Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 10px',
              background: 'rgba(0, 0, 0, 0.4)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              fontSize: '0.72rem',
              fontWeight: 600,
              color: '#94A3B8',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#10B981',
                  boxShadow: '0 0 6px #10B981',
                }}
              />
              <span style={{ color: '#F8FAFC' }}>Gesture Cam</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              {/* Settings / Sensitivity Button */}
              <button
                onClick={() => {
                  setShowSettings(!showSettings);
                  setShowHelp(false);
                  setShowCameraSelect(false);
                }}
                style={{
                  background: showSettings ? 'rgba(168, 85, 247, 0.25)' : 'none',
                  border: 'none',
                  color: showSettings ? '#C084FC' : '#94A3B8',
                  cursor: 'pointer',
                  padding: 2,
                  display: 'flex',
                  alignItems: 'center',
                }}
                title="Mouse Cursor & Scroll Speed (Range Sliders)"
              >
                <Sliders size={13} />
              </button>

              {availableCameras.length > 1 && (
                <button
                  onClick={() => {
                    setShowCameraSelect(!showCameraSelect);
                    setShowSettings(false);
                    setShowHelp(false);
                  }}
                  style={{
                    background: showCameraSelect ? 'rgba(56, 189, 248, 0.25)' : 'none',
                    border: 'none',
                    color: showCameraSelect ? '#38BDF8' : '#94A3B8',
                    cursor: 'pointer',
                    padding: '2px 4px',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  title="Switch Camera (Integrated Webcam vs Phone/V2503)"
                >
                  <Camera size={13} />
                </button>
              )}

              <button
                onClick={() => {
                  setShowHelp(!showHelp);
                  setShowSettings(false);
                  setShowCameraSelect(false);
                }}
                style={{
                  background: showHelp ? 'rgba(56, 189, 248, 0.25)' : 'none',
                  border: 'none',
                  color: showHelp ? '#38BDF8' : '#94A3B8',
                  cursor: 'pointer',
                  padding: 2,
                }}
                title="Gesture Guide"
              >
                <HelpCircle size={13} />
              </button>
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94A3B8',
                  cursor: 'pointer',
                  padding: 2,
                }}
                title={isMinimized ? 'Expand' : 'Minimize'}
              >
                {isMinimized ? <Maximize2 size={13} /> : <Minimize2 size={13} />}
              </button>
              <button
                onClick={toggleTouchless}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#EF4444',
                  cursor: 'pointer',
                  padding: 2,
                }}
                title="Turn off"
              >
                <X size={13} />
              </button>
            </div>
          </div>

          {/* Settings Panel: Mouse Sensitivity Range & Scroll Speed */}
          {showSettings && (
            <div
              style={{
                padding: '10px 12px',
                background: 'rgba(15, 23, 42, 0.98)',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                fontSize: '0.72rem',
                color: '#CBD5E1',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontWeight: 700, color: '#F8FAFC', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Gauge size={13} color="#C084FC" /> Cursor & Scroll Speed
                </span>
                <button
                  onClick={() => {
                    setPointerSpeed(1.3);
                    setScrollSpeed(1.0);
                    setInvertDirection(true);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#38BDF8',
                    fontSize: '0.65rem',
                    cursor: 'pointer',
                    padding: 0,
                    textDecoration: 'underline',
                  }}
                >
                  Reset
                </button>
              </div>

              {/* Pointer Speed Range */}
              <div style={{ marginBottom: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px', fontSize: '0.68rem' }}>
                  <span>Cursor Pointer Speed:</span>
                  <span style={{ color: '#C084FC', fontWeight: 700 }}>
                    {pointerSpeed.toFixed(1)}x {pointerSpeed < 1.0 ? '(Precise)' : pointerSpeed > 1.6 ? '(Fast)' : '(Normal)'}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.5"
                  step="0.1"
                  value={pointerSpeed}
                  onChange={(e) => setPointerSpeed(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#A855F7', cursor: 'pointer', height: '4px' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: '#64748B' }}>
                  <span>Slower (0.5x)</span>
                  <span>Normal (1.3x)</span>
                  <span>Faster (2.5x)</span>
                </div>
              </div>

              {/* Scroll Speed Range */}
              <div style={{ marginBottom: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px', fontSize: '0.68rem' }}>
                  <span>Vertical Scroll Speed:</span>
                  <span style={{ color: '#10B981', fontWeight: 700 }}>{scrollSpeed.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.5"
                  step="0.1"
                  value={scrollSpeed}
                  onChange={(e) => setScrollSpeed(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#10B981', cursor: 'pointer', height: '4px' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: '#64748B' }}>
                  <span>Gentle</span>
                  <span>Normal (1.0x)</span>
                  <span>Rapid</span>
                </div>
              </div>

              {/* Inverted Direction Toggle */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingTop: '6px',
                  borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.68rem', fontWeight: 600 }}>Scroll Direction:</span>
                  <span style={{ fontSize: '0.58rem', color: '#94A3B8' }}>
                    {invertDirection ? 'Up ➔ Scroll Down (Natural)' : 'Up ➔ Scroll Up (Standard)'}
                  </span>
                </div>
                <button
                  onClick={() => setInvertDirection(!invertDirection)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-glass)',
                    background: invertDirection ? 'rgba(16, 185, 129, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                    color: invertDirection ? '#34D399' : '#38BDF8',
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {invertDirection ? 'Natural' : 'Standard'}
                </button>
              </div>

              {/* Force Reset Hardware Button */}
              <div
                style={{
                  paddingTop: '8px',
                  marginTop: '8px',
                  borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <button
                  onClick={handleForceResetCamera}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '5px',
                    width: '100%',
                    padding: '5px 8px',
                    borderRadius: '6px',
                    background: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#F87171',
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                  title="Force releases any stuck Windows DirectShow camera handles and re-initializes"
                >
                  <RefreshCw size={11} /> Force Reset Camera Hardware
                </button>
              </div>
            </div>
          )}

          {/* Camera Selector Dropdown */}
          {showCameraSelect && availableCameras.length > 1 && (
            <div style={{ padding: '8px 10px', background: 'rgba(30, 41, 59, 0.98)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ fontSize: '0.68rem', color: '#94A3B8', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                <span>Select Camera Source:</span>
                <span style={{ color: '#38BDF8' }}>{availableCameras.length} found</span>
              </div>
              <select
                value={selectedCameraId}
                onChange={(e) => switchCamera(e.target.value)}
                style={{
                  width: '100%',
                  padding: '4px 6px',
                  borderRadius: '6px',
                  background: 'rgba(15, 23, 42, 0.95)',
                  color: '#FFF',
                  border: '1px solid rgba(255,255,255,0.2)',
                  fontSize: '0.72rem',
                }}
              >
                {availableCameras.map((cam, idx) => (
                  <option key={cam.deviceId || idx} value={cam.deviceId}>
                    {cam.label || `Camera ${idx + 1}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Video & Skeleton Canvas (Hidden if minimized) */}
          {!isMinimized && (
            <div style={{ position: 'relative', width: '100%', height: '135px', background: '#000' }}>
              <video
                ref={attachVideoRef}
                autoPlay
                playsInline
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: 'scaleX(-1)', // Mirror preview
                  opacity: 0.95,
                }}
              />
              <canvas
                ref={canvasRef}
                width={180}
                height={135}
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                }}
              />
            </div>
          )}

          {/* Footer Status & Quota */}
          <div style={{ padding: '6px 10px', fontSize: '0.72rem', background: 'rgba(0,0,0,0.2)' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '4px',
              }}
            >
              <span style={{ color: '#38BDF8', fontWeight: 600 }}>{currentGesture}</span>
              {isPremium ? (
                <span style={{ color: '#A855F7', fontWeight: 700 }}>💎 Unlimited</span>
              ) : (
                <span
                  style={{
                    color: quota.remaining <= 10 ? '#EF4444' : '#94A3B8',
                    fontWeight: 600,
                  }}
                >
                  {quota.remaining}/100 left
                </span>
              )}
            </div>

            {/* Quick gesture cheat sheet dropdown */}
            {showHelp && (
              <div
                style={{
                  marginTop: '6px',
                  padding: '8px',
                  borderRadius: '6px',
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  fontSize: '0.68rem',
                  lineHeight: '1.4',
                  color: '#CBD5E1',
                }}
              >
                <div>🤟/✌️ <b>2 or 3 Fingers:</b> Flick Left ➔ Next / Right ⬅ Prev</div>
                <div>✌️ <b>2 Fingers:</b> Auto-Scroll Joystick (Hold Up / Down)</div>
                <div>✊ <b>Closed Fist / Grab:</b> Stop & Lock Current Position</div>
                <div>👍 <b>Hold Thumbs Up:</b> Zoom In (+15%)</div>
                <div>👎 <b>Hold Thumbs Down:</b> Zoom Out (-15%)</div>
                <div>👆 <b>Index Finger:</b> Laser Pointer & Pinch Click (No Swipes)</div>
                <div>👌 <b>Pinch:</b> Click / Select</div>
                <div>🖐️ <b>Open Palm:</b> Ready / Standby</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. Quota Exhausted Modal Alert */}
      {showQuotaWarning && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999999,
            padding: '16px',
          }}
        >
          <div
            style={{
              maxWidth: '420px',
              width: '100%',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-glass)',
              borderRadius: '16px',
              padding: '24px',
              textAlign: 'center',
              boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
            }}
          >
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                background: 'rgba(168, 85, 247, 0.15)',
                color: '#A855F7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <Lock size={24} />
            </div>

            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0 0 8px' }}>
              Daily 100 Gestures Reached
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.5, margin: '0 0 20px' }}>
              You've utilized your 100 free touchless gestures for today! Your quota auto-resets tomorrow at midnight, or unlock unlimited touchless control right now with <b>EditoDoc Pro</b>.
            </p>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowQuotaWarning(false)}
                style={{ padding: '8px 16px' }}
              >
                Close
              </button>
              <button
                className="btn btn-primary"
                onClick={() => setShowQuotaWarning(false)}
                style={{
                  padding: '8px 20px',
                  background: 'linear-gradient(135deg, #8B5CF6, #EC4899)',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                💎 Unlimited Gestures Active
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
