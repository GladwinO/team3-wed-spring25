// HTML templates for map markers

const markerTemplates = {
    garage: `
        <div style="
            background-color: #2c3e50; 
            width: 18px;
            height: 18px;
            border-radius: 5px;
            display: flex; 
            justify-content: center; 
            align-items: center; 
            border: 1px solid white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.4);
        ">
            <i class="fas fa-car" style="
                color: white; 
                font-size: 9px;
                transform: rotate(-45deg);
            "></i>
        </div>
    `,
    meter: `
        <div style="
            background-color: #e74c3c; 
            width: 18px;
            height: 18px;
            border-radius: 5px;
            display: flex;
            justify-content: center;
            align-items: center;
            border: 1px solid white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.4);
        ">
            <i class="fas fa-parking" style="color: white; font-size: 9px;"></i>
        </div>
    `
};