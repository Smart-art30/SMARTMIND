document.addEventListener("DOMContentLoaded", function () {

    const button = document.getElementById("smartmind-chat-button");
    const windowBox = document.getElementById("smartmind-chat-window");
    const send = document.getElementById("smartmind-send");
    const input = document.getElementById("smartmind-input");
    const messages = document.getElementById("smartmind-messages");

    /*
     * Optional close button.
     *
     * If your header contains:
     *
     * <button id="smartmind-close">×</button>
     *
     * it will automatically work.
     */
    const closeButton = document.getElementById("smartmind-close");


    // =====================================================
    // SAFETY CHECK
    // =====================================================

    if (!button || !windowBox || !send || !input || !messages) {
        console.error("SmartMind AI chatbot elements not found.");
        return;
    }


    // =====================================================
    // OPEN CHAT
    // =====================================================

    function openChat() {

        windowBox.style.display = "flex";

        /*
         * Small delay allows the browser to finish
         * rendering the chatbot before focusing.
         */
        setTimeout(function () {

            input.focus();

            scrollToBottom();

        }, 100);

    }


    // =====================================================
    // CLOSE CHAT
    // =====================================================

    function closeChat() {

        windowBox.style.display = "none";

        /*
         * Remove focus so the mobile keyboard closes.
         */
        input.blur();

    }


    // =====================================================
    // TOGGLE CHAT
    // =====================================================

    function toggleChat() {

        const isOpen =
            window.getComputedStyle(windowBox).display !== "none";

        if (isOpen) {

            closeChat();

        } else {

            openChat();

        }

    }


    // =====================================================
    // CHAT BUTTON
    // =====================================================

    button.addEventListener("click", function () {

        toggleChat();

    });


    // =====================================================
    // CLOSE BUTTON
    // =====================================================

    if (closeButton) {

        closeButton.addEventListener("click", function () {

            closeChat();

        });

    }


    // =====================================================
    // SCROLL TO BOTTOM
    // =====================================================

    function scrollToBottom() {

        requestAnimationFrame(function () {

            messages.scrollTop = messages.scrollHeight;

        });

    }


    // =====================================================
    // ADD USER MESSAGE
    // =====================================================

    function addUserMessage(message) {

        const wrapper = document.createElement("div");

        wrapper.className = "smartmind-message user";


        const bubble = document.createElement("div");

        bubble.className = "smartmind-bubble";


        /*
         * IMPORTANT:
         *
         * textContent is used for learner messages.
         *
         * This prevents HTML/JavaScript injection.
         */

        bubble.textContent = message;


        wrapper.appendChild(bubble);

        messages.appendChild(wrapper);


        scrollToBottom();

    }


    // =====================================================
    // ADD AI MESSAGE
    // =====================================================

    function addAIMessage(html) {

        const wrapper = document.createElement("div");

        wrapper.className = "smartmind-message ai";


        const bubble = document.createElement("div");

        bubble.className = "smartmind-bubble";


        /*
         * Backend-generated HTML.
         *
         * Example:
         *
         * <strong>Coding</strong>
         * <p>Coding means...</p>
         * <ol>...</ol>
         */

        bubble.innerHTML = html;


        wrapper.appendChild(bubble);

        messages.appendChild(wrapper);


        scrollToBottom();

    }


    // =====================================================
    // ADD ERROR MESSAGE
    // =====================================================

    function addErrorMessage(message) {

        const wrapper = document.createElement("div");

        wrapper.className = "smartmind-message ai";


        const bubble = document.createElement("div");

        bubble.className = "smartmind-bubble";


        bubble.style.color = "#dc2626";

        bubble.textContent = message;


        wrapper.appendChild(bubble);

        messages.appendChild(wrapper);


        scrollToBottom();

    }


    // =====================================================
    // ADD TEMPORARY "THINKING" MESSAGE
    // =====================================================

    function addThinkingMessage() {

        const wrapper = document.createElement("div");

        wrapper.className =
            "smartmind-message ai smartmind-thinking";


        const bubble = document.createElement("div");

        bubble.className = "smartmind-bubble";

        bubble.textContent = "SmartMind AI is thinking...";


        wrapper.appendChild(bubble);

        messages.appendChild(wrapper);


        scrollToBottom();


        return wrapper;

    }


    // =====================================================
    // SEND MESSAGE
    // =====================================================

    async function sendMessage() {

        const message = input.value.trim();


        // Don't send empty messages

        if (!message) {

            return;

        }


        // -----------------------------------------------
        // Show learner message
        // -----------------------------------------------

        addUserMessage(message);


        // Clear input

        input.value = "";


        // -----------------------------------------------
        // Disable send button
        // -----------------------------------------------

        send.disabled = true;

        send.style.opacity = "0.6";

        send.style.cursor = "not-allowed";


        // -----------------------------------------------
        // Show thinking message
        // -----------------------------------------------

        const thinkingMessage =
            addThinkingMessage();


        try {

            // -------------------------------------------
            // Send request to Django
            // -------------------------------------------

            const response = await fetch(
                "/smartmind_ai/chat/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json",

                        "X-Requested-With":
                            "XMLHttpRequest"
                    },

                    body: JSON.stringify({
                        message: message
                    })
                }
            );


            // -------------------------------------------
            // Remove thinking message
            // -------------------------------------------

            if (thinkingMessage) {

                thinkingMessage.remove();

            }


            // -------------------------------------------
            // Handle HTTP errors
            // -------------------------------------------

            if (!response.ok) {

                /*
                 * Handle Gemini quota errors.
                 */

                if (response.status === 429) {

                    addErrorMessage(
                        "🤖 SmartMind AI is temporarily busy. Please try again later."
                    );

                    return;

                }


                if (response.status === 500) {

                    addErrorMessage(
                        "SmartMind AI is temporarily unavailable. Please try again later."
                    );

                    return;

                }


                if (response.status === 403) {

                    addErrorMessage(
                        "SmartMind AI access was denied. Please contact the administrator."
                    );

                    return;

                }


                throw new Error(
                    `Server returned ${response.status}`
                );

            }


            // -------------------------------------------
            // Read JSON response
            // -------------------------------------------

            const data = await response.json();


            // -------------------------------------------
            // Display AI response
            // -------------------------------------------

            if (data.reply) {

                addAIMessage(data.reply);

            } else {

                addErrorMessage(
                    "SmartMind AI returned an empty response."
                );

            }


        } catch (error) {

            console.error(
                "SmartMind AI Error:",
                error
            );


            // Remove thinking message if it still exists

            if (thinkingMessage) {

                thinkingMessage.remove();

            }


            addErrorMessage(
                "Sorry, I couldn't connect to SmartMind AI. Please try again."
            );


        } finally {

            // -------------------------------------------
            // Re-enable send button
            // -------------------------------------------

            send.disabled = false;

            send.style.opacity = "1";

            send.style.cursor = "pointer";


            /*
             * Don't force the keyboard open after every
             * response on mobile.
             *
             * Only keep focus if the chatbot is still open.
             */

            if (
                window.getComputedStyle(windowBox).display !== "none"
            ) {

                input.focus();

            }

        }

    }


    // =====================================================
    // SEND BUTTON
    // =====================================================

    send.addEventListener(
        "click",
        function () {

            sendMessage();

        }
    );


    // =====================================================
    // ENTER KEY
    // =====================================================

    input.addEventListener(
        "keydown",
        function (event) {

            /*
             * Enter sends the message.
             *
             * Shift + Enter creates a new line.
             */

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendMessage();

            }

        }
    );


    // =====================================================
    // MOBILE KEYBOARD HANDLING
    // =====================================================

    /*
     * Modern phones expose the visible viewport through
     * visualViewport.
     *
     * This helps prevent the chatbot from being pushed
     * behind the mobile keyboard.
     */

    if (window.visualViewport) {

        function updateMobileViewport() {

            document.documentElement.style.setProperty(
                "--smartmind-viewport-height",
                `${window.visualViewport.height}px`
            );

        }


        window.visualViewport.addEventListener(
            "resize",
            updateMobileViewport
        );


        window.visualViewport.addEventListener(
            "scroll",
            updateMobileViewport
        );


        updateMobileViewport();

    }


    // =====================================================
    // INITIAL STATE
    // =====================================================

    windowBox.style.display = "none";

});