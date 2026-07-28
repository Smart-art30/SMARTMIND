document.addEventListener("DOMContentLoaded", function () {

    const button = document.getElementById("smartmind-chat-button");
    const windowBox = document.getElementById("smartmind-chat-window");
    const send = document.getElementById("smartmind-send");
    const input = document.getElementById("smartmind-input");
    const messages = document.getElementById("smartmind-messages");

    button.onclick = function () {
        windowBox.style.display =
            windowBox.style.display === "block" ? "none" : "block";
    };

    async function sendMessage() {

        const message = input.value.trim();

        if (!message) return;

        messages.innerHTML += `
            <div style="text-align:right;margin:10px;">
                <b>You:</b><br>${message}
            </div>
        `;

        input.value = "";

        try {

            const response = await fetch("/smartmind_ai/chat/", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                },

                body: JSON.stringify({
                    message: message
                })

            });

            const data = await response.json();

            messages.innerHTML += `
                <div style="margin:10px;">
                    <b>🤖 SmartMind:</b><br>${data.reply}
                </div>
            `;

            messages.scrollTop = messages.scrollHeight;

        } catch (err) {

            messages.innerHTML += `
                <div style="color:red">
                    Error connecting to AI.
                </div>
            `;

            console.error(err);
        }

    }

    send.onclick = sendMessage;

    input.addEventListener("keypress", function(e){

        if(e.key==="Enter"){

            sendMessage();

        }

    });

});