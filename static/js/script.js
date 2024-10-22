document.addEventListener('DOMContentLoaded', function() {
    const newTaskForm = document.getElementById('new-task-form');
    const quadrants = {
        'urgent-important': document.querySelector('#urgent-important .task-list'),
        'not-urgent-important': document.querySelector('#not-urgent-important .task-list'),
        'urgent-not-important': document.querySelector('#urgent-not-important .task-list'),
        'not-urgent-not-important': document.querySelector('#not-urgent-not-important .task-list')
    };

    newTaskForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const taskName = document.getElementById('task-name').value;
        const urgent = document.getElementById('urgent').checked;
        const important = document.getElementById('important').checked;

        createTask(taskName, urgent, important);
    });

    function createTask(name, urgent, important) {
        const task = {
            name: name,
            priority: { urgent: urgent, important: important }
        };

        fetch('/task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(task),
        })
        .then(response => response.json())
        .then(data => {
            addTaskToQuadrant(data);
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }

    function addTaskToQuadrant(task) {
        const quadrantId = getQuadrantId(task.priority);
        const taskElement = createTaskElement(task);
        quadrants[quadrantId].appendChild(taskElement);
    }

    function getQuadrantId(priority) {
        if (priority.urgent && priority.important) return 'urgent-important';
        if (!priority.urgent && priority.important) return 'not-urgent-important';
        if (priority.urgent && !priority.important) return 'urgent-not-important';
        return 'not-urgent-not-important';
    }

    function createTaskElement(task) {
        const li = document.createElement('li');
        li.className = 'task-item';
        li.innerHTML = `
            ${task.name}
            <button onclick="deleteTask('${task._id}', this)">Delete</button>
        `;
        return li;
    }

    // Load existing tasks
    fetch('/task')
        .then(response => response.json())
        .then(tasks => {
            tasks.forEach(addTaskToQuadrant);
        })
        .catch((error) => {
            console.error('Error:', error);
        });
});

function deleteTask(taskId, button) {
    fetch(`/task/${taskId}`, {
        method: 'DELETE',
    })
    .then(response => response.json())
    .then(data => {
        button.parentElement.remove();
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}
