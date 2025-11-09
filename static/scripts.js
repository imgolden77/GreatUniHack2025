const videoFeed = document.getElementById('videoFeed');
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const feedbackDiv = document.getElementById('feedback');

// [신규] 모드 버튼
const frontalButton = document.getElementById('frontalButton');
const sideButton = document.getElementById('sideButton');

let analysisActive = false;
let feedbackInterval;


const updateFeedback = async () => {
    try {
        // 백엔드의 /feedback 엔드포인트 호출
        const response = await fetch('/feedback');
        if (!response.ok) throw new Error('Server not responding');
        const data = await response.json();

        if (feedbackDiv) feedbackDiv.textContent = data.message;

        // [수정] 피드백에서 'mode'를 받아와 버튼 UI 동기화
        if (data.mode === 'frontal') {
            frontalButton.classList.add('active');
            sideButton.classList.remove('active');
        } else if (data.mode === 'side') {
            sideButton.classList.add('active');
            frontalButton.classList.remove('active');
        }

        // [수정] 백엔드에서 분석이 멈춘 경우 (e.g. 작업 완료)
        if (analysisActive && data.active === false) {
            analysisActive = false;
            startButton.disabled = false;
            stopButton.disabled = true;
            // 모드 버튼도 다시 활성화
            frontalButton.disabled = false;
            sideButton.disabled = false;

            clearInterval(feedbackInterval);
            // videoFeed.src = ''; // 영상 스트림은 stop 버튼이 관리
        }

    } catch (e) {
        // 서버가 멈추거나 통신 오류가 발생했을 때
        if (feedbackDiv) feedbackDiv.textContent = '❌ Server connection error.';
        console.error("Feedback fetch error:", e);
        // 연결 오류 시 모든 인터벌 중지
        if (feedbackInterval) clearInterval(feedbackInterval);
    }
};

// [신규] 모드 변경 함수
const setMode = async (mode) => {
    if (analysisActive) return; // 분석 중에는 모드 변경 불가

    try {
        await fetch(`/control/set_view/${mode}`, { method: 'POST' });
        // 모드 변경 후 즉시 피드백을 업데이트하여 UI에 반영
        await updateFeedback();
    } catch (e) {
        console.error("Set mode error:", e);
        feedbackDiv.textContent = '❌ Could not set mode.';
    }
};

// [신규] 모드 버튼에 클릭 이벤트 할당
frontalButton.onclick = () => setMode('frontal');
sideButton.onclick = () => setMode('side');


// 분석 시작 함수
startButton.onclick = async () => {
    if (analysisActive) return;
    analysisActive = true;

    // [수정] 모든 컨트롤 버튼 비활성화
    startButton.disabled = true;
    stopButton.disabled = false;
    frontalButton.disabled = true;
    sideButton.disabled = true;

    // 1. FastAPI 백엔드에 분석 시작을 요청
    try {
        await fetch('/control/start', { method: 'POST' });

        // 2. 영상 스트림 시작 (캐시 방지용 타임스탬프 추가)
        videoFeed.src = `/video_feed?t=${new Date().getTime()}`;

        // 3. 피드백 업데이트 시작
        if (feedbackInterval) clearInterval(feedbackInterval); // 혹시 모를 기존 인터벌 제거
        feedbackInterval = setInterval(updateFeedback, 500);
        if (feedbackDiv) feedbackDiv.textContent = 'Analysis starting...';

    } catch (e) {
        if (feedbackDiv) feedbackDiv.textContent = '❌ Failed to start analysis. Check server.';
        analysisActive = false;
        startButton.disabled = false;
        stopButton.disabled = true;
        frontalButton.disabled = false;
        sideButton.disabled = false;
    }
};

// 분석 정지 함수
stopButton.onclick = async () => {
    if (!analysisActive) return;
    analysisActive = false;

    // [수정] 컨트롤 버튼 상태 복원
    startButton.disabled = false;
    stopButton.disabled = true;
    frontalButton.disabled = false;
    sideButton.disabled = false;

    // 1. 타이머 정지
    clearInterval(feedbackInterval);

    // 2. FastAPI 백엔드에 분석 정지를 요청
    await fetch('/control/stop', { method: 'POST' });

    // 3. 영상 스트림 정지 (src를 비우면 alt 텍스트가 나옴)
    videoFeed.src = '';

    // 4. 피드백을 즉시 업데이트하여 "Stopped" 메시지 표시
    await updateFeedback();
};

// --- [신규] 페이지 로드 시 초기 상태 동기화 ---
// 페이지가 로드될 때 백엔드의 현재 모드와 상태를 가져옵니다.
document.addEventListener('DOMContentLoaded', updateFeedback);