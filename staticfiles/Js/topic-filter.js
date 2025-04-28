function filterTopics(searchTerm) {
    searchTerm = searchTerm.toLowerCase();
    const topics = document.querySelectorAll('.topic-item');
    
    topics.forEach(topic => {
        const text = topic.textContent.toLowerCase();
        const letterGroup = topic.closest('.letter-group');
        
        if (text.includes(searchTerm)) {
            topic.style.display = 'flex';
            if (letterGroup) letterGroup.style.display = 'block';
        } else {
            topic.style.display = 'none';
            // Hide letter group if all topics are hidden
            if (letterGroup && 
                !Array.from(letterGroup.querySelectorAll('.topic-item'))
                    .some(t => t.style.display !== 'none')) {
                letterGroup.style.display = 'none';
            }
        }
    });
}