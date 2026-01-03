document.addEventListener('DOMContentLoaded', () => {

    // Elements
    const analysisForm = document.getElementById('analysis-form');
    const resultsArea = document.getElementById('results-area');
    const resultsContainer = document.getElementById('results-container');
    const analysisView = document.getElementById('analysis-view');
    const roadmapView = document.getElementById('roadmap-view');
    const backBtn = document.getElementById('back-to-analysis');

    const bodySvg = document.querySelector('.body-svg');
    const systemConfSpan = document.getElementById('sys-conf');
    const dataPtsSpan = document.getElementById('data-pts');

    let currentPatientId = null;

    // Handle Form Submission
    analysisForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('p-name').value;
        const age = document.getElementById('p-age').value;
        const sex = document.getElementById('p-sex').value;
        const symptomsRaw = document.getElementById('p-symptoms').value;

        const symptoms = symptomsRaw.split(',').map(s => s.trim()).filter(s => s);

        // UI Feedback
        const btn = document.getElementById('analyze-btn');
        const originalBtnText = btn.innerHTML;
        btn.innerHTML = 'Analyzing...';
        btn.disabled = true;

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, age, sex, symptoms })
            });

            const data = await response.json();
            currentPatientId = data.patient_id;

            renderResults(data.results);
            updateSidePanel(data.results, symptoms.length);
            updateAnatomy(symptoms);

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during analysis.');
        } finally {
            btn.innerHTML = originalBtnText;
            btn.disabled = false;
        }
    });

    // Render Analysis Results
    function renderResults(results) {
        resultsContainer.innerHTML = '';

        if (results.length === 0) {
            resultsContainer.innerHTML = '<p style="color:var(--text-muted)">No specific conditions matched. Please assume general viral or consult a specialist.</p>';
        }

        results.forEach(item => {
            const card = document.createElement('div');
            card.className = 'result-card';

            card.innerHTML = `
                <div class="result-header">
                    <div class="disease-name">${item.name}</div>
                    <div class="prob-tag" style="opacity: ${0.5 + (item.probability / 200)}">${item.probability}% Probable</div>
                </div>
                <div class="explanation">
                    <strong>Why?</strong> ${item.explanation}
                </div>
                 <div class="explanation">
                    <strong>Suggested Tests:</strong> ${item.suggested_tests.join(', ')}
                </div>
                <button class="lock-btn" onclick="lockDisease('${item.name}')">
                    🔒 Select & Plan Care
                </button>
            `;
            resultsContainer.appendChild(card);
        });

        resultsArea.classList.remove('hidden');
        resultsArea.scrollIntoView({ behavior: 'smooth' });
    }

    // Lock Disease & Show Roadmap
    window.lockDisease = async (diseaseName) => {
        if (!currentPatientId) return;

        try {
            const response = await fetch('/api/roadmap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ disease: diseaseName, patient_id: currentPatientId })
            });

            const data = await response.json();
            renderRoadmap(diseaseName, data.roadmap);

            // Switch Views
            analysisView.classList.add('hidden');
            roadmapView.classList.remove('hidden');
            window.scrollTo(0, 0);

        } catch (error) {
            console.error('Error fetching roadmap:', error);
        }
    };

    function renderRoadmap(disease, roadmap) {
        document.getElementById('locked-disease').textContent = disease;

        // Populate lists
        const fillList = (id, items) => {
            const ul = document.getElementById(id);
            ul.innerHTML = '';
            if (items) {
                items.forEach(i => {
                    const li = document.createElement('li');
                    li.textContent = i;
                    ul.appendChild(li);
                });
            } else {
                ul.innerHTML = '<li>No specific data available.</li>';
            }
        };

        fillList('roadmap-meds', roadmap.medication);
        fillList('roadmap-lifestyle', roadmap.lifestyle);
        fillList('roadmap-monitoring', roadmap.monitoring);

        // Summary
        const pName = document.getElementById('p-name').value;
        const pAge = document.getElementById('p-age').value;
        document.getElementById('roadmap-patient-summary').textContent = `${pName}, ${pAge}y`;
    }

    // Update Side Panel
    function updateSidePanel(results, symptomCount) {
        dataPtsSpan.textContent = symptomCount + " Symptoms";
        if (results.length > 0) {
            systemConfSpan.textContent = results[0].probability > 40 ? "Moderate" : "Low";
            systemConfSpan.style.color = results[0].probability > 40 ? "var(--primary-color)" : "var(--text-muted)";
        } else {
            systemConfSpan.textContent = "--";
        }
    }

    // Visual Anatomy Mock Logic
    function updateAnatomy(symptoms) {
        // Simple mock: if 'head' in symptoms, make head red. If 'chest', make body yellow/red.
        const s = symptoms.join(' ').toLowerCase();
        const head = document.querySelector('.body-part.head');
        const torso = document.querySelector('.body-part.torso-limbs');

        head.style.fill = '#e9ecef';
        torso.style.fill = '#e9ecef';

        if (s.includes('head') || s.includes('migraine') || s.includes('vision')) {
            head.style.fill = '#ffc107'; // Yellow
            if (s.includes('severe') || s.includes('blindness')) head.style.fill = '#dc3545'; // Red
        }

        if (s.includes('chest') || s.includes('heart') || s.includes('stomach') || s.includes('abdominal')) {
            torso.style.fill = '#ffc107';
            if (s.includes('pain') && s.includes('chest')) torso.style.fill = '#dc3545';
        }
    }

    // Back Button
    backBtn.addEventListener('click', () => {
        roadmapView.classList.add('hidden');
        analysisView.classList.remove('hidden');
    });

});
