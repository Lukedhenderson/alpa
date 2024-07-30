document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatBox = document.getElementById("chat-box");

    // Ensure chatBox is hidden initially
    chatBox.style.display = "none";

    chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const userInput = chatInput.value.trim();
        if (userInput === "") return;

        // Append user message
        appendMessage("You", userInput, "user");

        // Clear input
        chatInput.value = "";

        // Send user input to the backend
        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ message: userInput }),
            });

            if (response.ok) {
                const data = await response.json();
                appendMessage("AI Expert", data.response, "bot");
            } else {
                appendMessage("AI Expert", "An error occurred while communicating with the server.", "bot");
            }
        } catch (error) {
            console.error("Error:", error);
            appendMessage("AI Expert", "An error occurred while communicating with the server.", "bot");
        }
    });

    function appendMessage(sender, content, senderClass) {
        // Create message container
        const messageContainer = document.createElement("div");
        messageContainer.className = `message ${senderClass}`;

        // Create label and content elements
        const label = document.createElement("span");
        label.className = `${senderClass}-label`;
        label.textContent = `${sender}: `;
        label.style.fontWeight = "bold";

        const messageContent = document.createElement("span");
        try {
            messageContent.innerHTML = marked.parse(content);
        } catch (error) {
            console.error("Error parsing with marked:", error);
            messageContent.textContent = "Error parsing message.";
        }

        // Append label and content to the message container
        messageContainer.appendChild(label);
        messageContainer.appendChild(messageContent);

        // Append message container to the chat box
        chatBox.appendChild(messageContainer);

        // Ensure the chat box becomes visible
        chatBox.style.display = "block";
        chatBox.scrollTop = chatBox.scrollHeight; // Scroll to the bottom
    }
});