
document.addEventListener("DOMContentLoaded", function () {

    const button = document.getElementById("smartmind-chat-button");
    const windowBox = document.getElementById("smartmind-chat-window");
    const send = document.getElementById("smartmind-send");
    const input = document.getElementById("smartmind-input");
    const messages = document.getElementById("smartmind-messages");


    // =========================================================
    // OPEN / CLOSE CHAT
    // =========================================================

    button.onclick = function () {

        if (windowBox.style.display === "flex") {
            windowBox.style.display = "none";
        } else {
            windowBox.style.display = "flex";
            input.focus();
        }

    };


    // =========================================================
    // ADD USER MESSAGE
    // =========================================================

    function addUserMessage(message) {

        const wrapper = document.createElement("div");

        wrapper.className = "smartmind-message user";

        const bubble = document.createElement("div");

        bubble.className = "smartmind-bubble";

        // IMPORTANT:
        // Use textContent for learner messages.
        // This prevents the learner from injecting HTML/JavaScript.

        bubble.textContent = message;

        wrapper.appendChild(bubble);

        messages.appendChild(wrapper);

        messages.scrollTop = messages.scrollHeight;
    }


    // =========================================================
    // ADD AI MESSAGE
    // =========================================================

    function addAIMessage(html) {

        const wrapper = document.createElement("div");

        wrapper.className = "smartmind-message ai";

        const bubble = document.createElement("div");

        bubble.className = "smartmind-bubble";

        /*
         * The backend should already have converted Gemini's
         * Markdown into HTML.
         *
         * The HTML is inserted here so that:
         *
         * <strong>text</strong>
         *
         * becomes bold text,
         *
         * <h3>Heading</h3>
         *
         * becomes a heading,
         *
         * <ol>...</ol>
         *
         * becomes a numbered list.
         */

        bubble.innerHTML = html;

        wrapper.appendChild(bubble);

        messages.appendChild(wrapper);

        messages.scrollTop = messages.scrollHeight;
    }


    // =========================================================
    // ADD ERROR MESSAGE
    // =========================================================

    function addErrorMessage(message) {

        const wrapper = document.createElement("div");

        wrapper.className = "smartmind-message ai";

        const bubble = document.createElement("div");

        bubble.className = "smartmind-bubble";

        bubble.style.color = "#dc2626";

        bubble.textContent = message;

        wrapper.appendChild(bubble);

        messages.appendChild(wrapper);

        messages.scrollTop = messages.scrollHeight;
    }


    // =========================================================
    // SEND MESSAGE
    // =========================================================

    async function sendMessage() {

        const message = input.value.trim();

        if (!message) {
            return;
        }


        // Show learner message

        addUserMessage(message);

        input.value = "";

        input.focus();


        // Disable button while waiting

        send.disabled = true;

        send.style.opacity = "0.6";


        try {

            const response = await fetch(
                "/smartmind_ai/chat/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json",
                    },

                    body: JSON.stringify({
                        message: message
                    })
                }
            );


            // Check HTTP status

            if (!response.ok) {

                throw new Error(
                    `Server returned ${response.status}`
                );

            }


            const data = await response.json();


            // Make sure a reply exists

            if (data.reply) {

                addAIMessage(data.reply);

            } else {

                addErrorMessage(
                    "SmartMind AI returned an empty response."
                );

            }


        } catch (err) {

            console.error(
                "SmartMind AI Error:",
                err
            );

            addErrorMessage(
                "Sorry, I couldn't connect to SmartMind AI. Please try again."
            );

        } finally {

            // Re-enable send button

            send.disabled = false;

            send.style.opacity = "1";

            input.focus();

        }

    }


    // =========================================================
    // SEND BUTTON
    // =========================================================

    send.onclick = sendMessage;


    // =========================================================
    // ENTER KEY
    // =========================================================

    input.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Enter") {

                event.preventDefault();

                sendMessage();

            }

        }
    );

});
